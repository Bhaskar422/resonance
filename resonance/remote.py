"""Talk to a Resonance server from the command line: sign in, upload a clip, list and download runs.

The server and access token come from, in order: --server/--token, RESONANCE_SERVER and
RESONANCE_TOKEN, then what `resonance login` saved in ~/.config/resonance/credentials.json
(readable only by you).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path

import httpx

DEFAULT_SERVER = "http://127.0.0.1:8000"


class RemoteError(Exception):
    pass


def credentials_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return root / "resonance" / "credentials.json"


def saved() -> dict:
    p = credentials_path()
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def save(server: str, token: str, email: str | None) -> Path:
    p = credentials_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch(mode=0o600, exist_ok=True)
    p.chmod(0o600)
    p.write_text(json.dumps({"server": server, "token": token, "email": email}, indent=1))
    return p


def forget() -> bool:
    p = credentials_path()
    if p.exists():
        p.unlink()
        return True
    return False


class Client:
    def __init__(self, server: str | None = None, token: str | None = None):
        s = saved()
        self.server = (server or os.environ.get("RESONANCE_SERVER") or s.get("server") or DEFAULT_SERVER).rstrip("/")
        self.token = token or os.environ.get("RESONANCE_TOKEN") or (s.get("token") if s.get("server", "").rstrip("/") == self.server else None)
        self.http = httpx.Client(base_url=self.server, timeout=httpx.Timeout(30, read=300), follow_redirects=False)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def request(self, method: str, path: str, **kw) -> httpx.Response:
        try:
            r = self.http.request(method, path, headers=self._headers(), **kw)
        except httpx.ConnectError:
            raise RemoteError(f"cannot reach {self.server}; is `resonance serve` running there?") from None
        if r.status_code == 401:
            raise RemoteError(f"not signed in to {self.server}; run `resonance login --server {self.server}`")
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail")
            except ValueError:
                detail = None
            raise RemoteError(detail or f"{r.status_code} {r.reason_phrase}")
        return r

    def json(self, method: str, path: str, **kw):
        return self.request(method, path, **kw).json()

    # ---- sign in through the browser ----
    def device_login(self, name: str, show: Callable[[str, str], None], timeout_s: float = 600) -> dict:
        d = self.json("POST", "/api/cli/device", json={"name": name})
        show(d["user_code"], d["verification_uri"])
        deadline = time.time() + min(timeout_s, d.get("expires_in", 600))
        while time.time() < deadline:
            time.sleep(d.get("interval", 2))
            r = self.http.post("/api/cli/poll", json={"code": d["device_code"]})
            if r.status_code == 200:
                got = r.json()
                self.token = got["token"]
                return got
            if r.status_code == 404:
                break
        raise RemoteError("the code expired before it was approved; run resonance login again")

    def me(self) -> dict:
        return self.json("GET", "/api/me")

    # ---- runs ----
    def runs(self) -> list[dict]:
        return self.json("GET", "/api/runs")

    def run(self, run: str) -> dict:
        return self.json("GET", f"/api/runs/{run}")

    def upload(self, video: Path, fields: dict, accel: Path | None = None, manual: Path | None = None) -> str:
        files = {"video": (video.name, video.open("rb"), "application/octet-stream")}
        if accel:
            files["accel"] = (accel.name, accel.open("rb"), "text/csv")
        if manual:
            files["manual"] = (manual.name, manual.open("rb"), "application/pdf")
        try:
            data = {k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in fields.items() if v is not None}
            return self.json("POST", "/api/analyze", data=data, files=files)["job"]
        finally:
            for f in files.values():
                f[1].close()

    def wait(self, job: str, on_stage: Callable[[str], None], poll_s: float = 1.5) -> dict:
        seen: set[str] = set()
        while True:
            j = self.json("GET", f"/api/jobs/{job}")
            for s in j.get("stages", []):
                if s not in seen:
                    seen.add(s)
                    on_stage(s)
            if j["status"] in ("done", "error"):
                return j
            time.sleep(poll_s)

    def download(self, run: str, dest: Path) -> list[Path]:
        detail = self.run(run)
        dest.mkdir(parents=True, exist_ok=True)
        out = []
        for name, url in sorted(detail["files"].items()):
            path = dest / name
            with self.http.stream("GET", url, headers=self._headers()) as r:
                if r.status_code != 200:
                    continue
                with path.open("wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
            out.append(path)
        return out

    def report_url(self, run: str) -> str:
        return f"{self.server}/app#/runs/{run}"

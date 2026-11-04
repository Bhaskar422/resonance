"""Accounts: sign-up and sign-in, who sees which runs, access tokens and the CLI login."""

import json

import pytest
from fastapi.testclient import TestClient

from resonance import auth, server


def _run(root, name):
    d = root / name
    d.mkdir()
    (d / "report.json").write_text(json.dumps({
        "run": name, "input": f"{name}.mov", "machine": "fan", "mask": {"prompt": "fan"},
        "vibration": {"dominant": {"freq_hz": 17.0, "amplitude": 0.2, "snr": 9.0}},
    }))
    (d / "key_frame.png").write_bytes(b"png")


@pytest.fixture
def out(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "OUT", tmp_path)
    monkeypatch.delenv("RESONANCE_AUTH", raising=False)
    _run(tmp_path, "shared-example")
    return tmp_path


def _user(email, password="correct horse"):
    c = TestClient(server.app)
    r = c.post("/api/auth/signup", json={"email": email, "password": password, "name": email.split("@")[0]})
    assert r.status_code == 200, r.text
    return c


def test_everything_needs_an_account(out):
    c = TestClient(server.app)
    for path in ("/api/runs", "/api/runs/shared-example", "/files/shared-example/key_frame.png", "/api/costs", "/api/me"):
        assert c.get(path).status_code == 401, path
    assert c.get("/api/health").status_code == 200
    assert c.get("/api/auth/config").json()["required"] is True


def test_sign_up_sign_in_and_out(out):
    c = _user("Ada@Example.com")
    me = c.get("/api/me").json()
    assert me["email"] == "ada@example.com" and me["admin"] == 1 and me["has_password"]  # first account is the admin
    assert "password" not in me
    assert TestClient(server.app).post("/api/auth/signup", json={"email": "ada@example.com", "password": "another one"}).status_code == 400
    assert TestClient(server.app).post("/api/auth/signup", json={"email": "bob@example.com", "password": "short"}).status_code == 400
    c.post("/api/auth/signout")
    assert c.get("/api/me").status_code == 401
    assert c.post("/api/auth/signin", json={"email": "ada@example.com", "password": "wrong password"}).status_code == 401
    assert c.post("/api/auth/signin", json={"email": "ada@example.com", "password": "correct horse"}).status_code == 200
    assert c.get("/api/me").status_code == 200


def test_repeated_wrong_passwords_are_slowed_down(out):
    _user("ada@example.com")
    c = TestClient(server.app)
    codes = [c.post("/api/auth/signin", json={"email": "ada@example.com", "password": "nope nope"}).status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]


def test_users_see_their_own_runs_and_the_shared_examples(out):
    admin, ada, bob = _user("admin@example.com"), _user("ada@example.com"), _user("bob@example.com")
    ids = {e: c.get("/api/me").json()["id"] for e, c in (("ada", ada), ("bob", bob))}
    _run(out, "ada-run")
    server.accounts().set_owner("ada-run", ids["ada"])

    assert {r["run"] for r in ada.get("/api/runs").json()} == {"ada-run", "shared-example"}
    assert {r["run"] for r in bob.get("/api/runs").json()} == {"shared-example"}
    assert {r["run"] for r in admin.get("/api/runs").json()} == {"ada-run", "shared-example"}
    mine = {r["run"]: (r["mine"], r["shared"]) for r in ada.get("/api/runs").json()}
    assert mine == {"ada-run": (True, False), "shared-example": (False, True)}
    assert bob.get("/files/ada-run/key_frame.png").status_code == 404
    assert ada.get("/files/ada-run/key_frame.png").status_code == 200
    assert bob.post("/api/runs/shared-example/diagnose").status_code == 403  # examples are read-only
    assert bob.post("/api/runs/ada-run/diagnose").status_code == 404


def test_access_tokens_for_the_cli_and_app(out):
    c = _user("ada@example.com")
    made = c.post("/api/tokens", json={"name": "laptop"}).json()
    assert made["token"].startswith("rsn_") and made["info"]["name"] == "laptop"
    cli = TestClient(server.app)
    bearer = {"Authorization": f"Bearer {made['token']}"}
    assert cli.get("/api/me", headers=bearer).json()["email"] == "ada@example.com"
    listed = c.get("/api/tokens").json()
    assert [t["name"] for t in listed] == ["laptop"] and listed[0]["last_used"] and "hash" not in listed[0]
    assert c.delete(f"/api/tokens/{made['info']['id']}").status_code == 200
    assert cli.get("/api/me", headers=bearer).status_code == 401

    app_login = cli.post("/api/auth/token", json={"email": "ada@example.com", "password": "correct horse", "name": "iPhone"}).json()
    assert cli.get("/api/me", headers={"Authorization": f"Bearer {app_login['token']}"}).status_code == 200


def test_deleting_an_account_erases_its_runs_and_uploads(out):
    ada, bob = _user("ada@example.com"), _user("bob@example.com")
    ids = {e: c.get("/api/me").json()["id"] for e, c in (("ada", ada), ("bob", bob))}
    token = ada.post("/api/tokens", json={"name": "laptop"}).json()["token"]
    for who in ("ada", "bob"):
        _run(out, f"{who}-run")
        upload = out / "uploads" / f"{who}-job"
        upload.mkdir(parents=True)
        (upload / "clip.mov").write_bytes(b"mov")
        report = json.loads((out / f"{who}-run" / "report.json").read_text())
        (out / f"{who}-run" / "report.json").write_text(json.dumps({**report, "input": str(upload / "clip.mov")}))
        server.accounts().set_owner(f"{who}-run", ids[who])

    r = ada.delete("/api/me")
    assert r.status_code == 200 and r.json()["runs_deleted"] == 1
    assert not (out / "ada-run").exists() and not (out / "uploads" / "ada-job").exists()
    assert (out / "bob-run").exists() and (out / "uploads" / "bob-job").exists() and (out / "shared-example").exists()
    assert ada.get("/api/me").status_code == 401
    assert TestClient(server.app).get("/api/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert TestClient(server.app).post("/api/auth/signin", json={"email": "ada@example.com", "password": "correct horse"}).status_code == 401
    assert _user("ada@example.com").get("/api/me").json()["admin"] == 0  # the email can sign up again, as a new account


def test_cli_login_through_the_browser(out):
    browser = _user("ada@example.com")
    cli = TestClient(server.app)
    d = cli.post("/api/cli/device", json={"name": "resonance CLI on laptop"}).json()
    assert d["verification_uri"].endswith(f"/app#/link?code={d['user_code']}")
    assert cli.post("/api/cli/poll", json={"code": d["device_code"]}).status_code == 202
    assert browser.get(f"/api/cli/device/{d['user_code']}").json()["name"] == "resonance CLI on laptop"
    assert browser.post("/api/cli/approve", json={"code": d["user_code"]}).status_code == 200
    got = cli.post("/api/cli/poll", json={"code": d["device_code"]})
    assert got.status_code == 200 and got.json()["user"]["email"] == "ada@example.com"
    assert cli.get("/api/me", headers={"Authorization": f"Bearer {got.json()['token']}"}).status_code == 200
    assert cli.post("/api/cli/poll", json={"code": d["device_code"]}).status_code == 404  # handed out once
    assert browser.post("/api/cli/approve", json={"code": d["user_code"]}).status_code == 404


def test_provider_sign_in_links_by_verified_email_only(tmp_path):
    a = auth.Accounts(tmp_path / "a.db")
    squatter = a.sign_up("ada@example.com", "squatter password")
    raw = a.new_session(squatter["id"])
    # Google proves the real Ada owns the address: same account, but the squatter's password
    # and sessions stop working.
    ada = a.sign_in_with("google", "g-123", "ada@example.com", True, "Ada", None)
    assert ada["id"] == squatter["id"] and ada["password"] is None and ada["email_verified"] == 1
    assert a.session_user(raw) is None
    with pytest.raises(auth.AuthError):
        a.sign_in("ada@example.com", "squatter password")
    assert a.sign_in_with("google", "g-123", None, False, None, None)["id"] == ada["id"]  # linked now
    with pytest.raises(auth.AuthError):
        a.sign_in_with("github", "gh-9", "eve@example.com", False, "Eve", None)  # unverified: no account
    assert a.sign_in_with("github", "gh-9", "eve@example.com", True, "Eve", None)["email"] == "eve@example.com"


def test_oauth_is_offered_only_when_configured(out, monkeypatch):
    for k in ("RESONANCE_GITHUB_CLIENT_ID", "RESONANCE_GITHUB_CLIENT_SECRET", "RESONANCE_GOOGLE_CLIENT_ID", "RESONANCE_GOOGLE_CLIENT_SECRET", "RESONANCE_PUBLIC_URL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    c = TestClient(server.app)
    assert c.get("/api/auth/config").json()["providers"] == {"github": False, "google": False}
    assert c.get("/api/auth/github/start", follow_redirects=False).status_code == 400
    monkeypatch.setenv("RESONANCE_GITHUB_CLIENT_ID", "id123")
    monkeypatch.setenv("RESONANCE_GITHUB_CLIENT_SECRET", "secret")
    r = c.get("/api/auth/github/start?next=//evil.example", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].startswith("https://github.com/login/oauth/authorize?client_id=id123")
    assert "code_challenge_method=S256" in r.headers["location"] and "redirect_uri=http%3A%2F%2Ftestserver%2Fapi%2Fauth%2Fgithub%2Fcallback" in r.headers["location"]
    # A callback whose state did not start in this browser is refused.
    r = TestClient(server.app).get("/api/auth/github/callback?code=x&state=forged", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].startswith("/app?auth_error=")


def test_accounts_can_be_turned_off(out, monkeypatch):
    monkeypatch.setenv("RESONANCE_AUTH", "off")
    c = TestClient(server.app)
    assert c.get("/api/me").json()["name"] == "Local"
    assert [r["run"] for r in c.get("/api/runs").json()] == ["shared-example"]


def test_daily_spend_caps(out, monkeypatch):
    admin, ada = _user("admin@example.com"), _user("ada@example.com")
    monkeypatch.setenv("RESONANCE_DAILY_DIAGNOSES", "1")
    ada_id = ada.get("/api/me").json()["id"]
    _run(out, "ada-run"); server.accounts().set_owner("ada-run", ada_id)
    monkeypatch.setattr(server, "_pool", type("P", (), {"submit": lambda self, *a, **k: None})())
    assert ada.post("/api/runs/ada-run/diagnose").status_code == 200
    r = ada.post("/api/runs/ada-run/diagnose")
    assert r.status_code == 429 and "1 diagnoses per account per day" in r.json()["detail"]
    assert ada.get("/api/me").json()["usage"]["diagnosis"] == {"used": 1, "limit": 1}
    # the site-wide budget stops everyone, admins included
    (out / "costs.jsonl").write_text(json.dumps({"ts": __import__("time").strftime("%Y-%m-%dT%H:%M:%S"), "est_cost_usd": 2.5}) + "\n")
    monkeypatch.setenv("RESONANCE_DAILY_BUDGET_USD", "2")
    _run(out, "admin-run")
    assert admin.post("/api/runs/admin-run/diagnose").status_code == 429


def test_example_clips_and_showcase_runs(out, monkeypatch, tmp_path_factory):
    ex = tmp_path_factory.mktemp("examples")
    (ex / "fan-putty").mkdir()
    (ex / "fan-putty" / "clip.mov").write_bytes(b"mov")
    (ex / "fan-putty" / "accel.csv").write_text("t,x\n")
    (ex / "fan-putty" / "example.json").write_text(json.dumps({"title": "Fan with putty", "video": "clip.mov", "accel": "accel.csv", "prompt": "fan", "machine": "Desk fan", "start": 1, "duration": 10}))
    monkeypatch.setenv("RESONANCE_EXAMPLES", str(ex))
    owner, bob, eve = _user("owner@example.com"), _user("bob@example.com"), _user("eve@example.com")
    listed = bob.get("/api/examples").json()
    assert [e["id"] for e in listed] == ["fan-putty"] and listed[0]["accel"] == "accel.csv"
    jobs = []
    monkeypatch.setattr(server, "_pool", type("P", (), {"submit": lambda self, fn, job, video, form: jobs.append((job, video, form))})())
    r = bob.post("/api/analyze", data={"example": "fan-putty", "diagnose": "false"})
    assert r.status_code == 200, r.text
    job, video, form = jobs[0]
    assert video.name == "clip.mov" and video.read_bytes() == b"mov" and form["accel"].name == "accel.csv"
    assert form["prompt"] == "fan" and form["start"] == 1 and job.owner == bob.get("/api/me").json()["id"]
    assert bob.post("/api/analyze", data={"example": "nope"}).status_code == 404
    assert bob.post("/api/analyze", data={}).status_code == 400
    # runs of the showcase account are open to everyone, read-only; other accounts stay private
    ids = {e: c.get("/api/me").json()["id"] for e, c in (("owner", owner), ("bob", bob))}
    _run(out, "owner-run"); server.accounts().set_owner("owner-run", ids["owner"])
    _run(out, "bob-run"); server.accounts().set_owner("bob-run", ids["bob"])
    monkeypatch.setenv("RESONANCE_SHOWCASE_EMAILS", "owner@example.com")
    seen = {r["run"]: r["shared"] for r in eve.get("/api/runs").json()}
    assert seen == {"owner-run": True, "shared-example": True}
    assert eve.post("/api/runs/owner-run/diagnose").status_code == 403

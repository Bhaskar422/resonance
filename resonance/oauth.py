"""Sign in with GitHub or Google (OAuth 2.0 authorization code flow, server side).

A provider is offered only when its app credentials are in the environment (.env):

    RESONANCE_GITHUB_CLIENT_ID / RESONANCE_GITHUB_CLIENT_SECRET
        github.com > Settings > Developer settings > OAuth Apps; callback URL
        <public url>/api/auth/github/callback
    RESONANCE_GOOGLE_CLIENT_ID / RESONANCE_GOOGLE_CLIENT_SECRET
        console.cloud.google.com > APIs & Services > Credentials > OAuth client ID (Web);
        authorized redirect URI <public url>/api/auth/google/callback

RESONANCE_PUBLIC_URL sets <public url> (default: the address the browser used).

Endpoints and fields follow the providers' documentation: GitHub's "Authorizing OAuth apps"
(with PKCE) plus GET /user and GET /user/emails; Google's OpenID Connect discovery document,
whose token and userinfo endpoints are read at run time.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

GITHUB_AUTHORIZE = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN = "https://github.com/login/oauth/access_token"
GITHUB_API = "https://api.github.com"
GITHUB_HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"}
GOOGLE_DISCOVERY = "https://accounts.google.com/.well-known/openid-configuration"
STATE_TTL = 600


@dataclass
class Identity:
    provider: str
    subject: str
    email: str | None
    verified: bool
    name: str | None
    avatar: str | None


class OAuthError(Exception):
    pass


def configured() -> dict[str, bool]:
    from dotenv import load_dotenv

    load_dotenv()
    return {p: bool(os.environ.get(f"RESONANCE_{p.upper()}_CLIENT_ID") and os.environ.get(f"RESONANCE_{p.upper()}_CLIENT_SECRET")) for p in ("github", "google")}


def _creds(provider: str) -> tuple[str, str]:
    if not configured().get(provider):
        raise OAuthError(f"sign-in with {provider.capitalize() if provider != 'github' else 'GitHub'} is not set up on this server")
    return os.environ[f"RESONANCE_{provider.upper()}_CLIENT_ID"], os.environ[f"RESONANCE_{provider.upper()}_CLIENT_SECRET"]


class States:
    """Pending sign-ins: state -> PKCE verifier and where to go afterwards."""

    def __init__(self):
        self._s: dict[str, dict] = {}
        self._lock = threading.Lock()

    def new(self, provider: str, next_url: str) -> tuple[str, str]:
        state, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(48)
        with self._lock:
            now = time.time()
            for k in [k for k, v in self._s.items() if v["at"] < now - STATE_TTL]:
                del self._s[k]
            self._s[state] = {"provider": provider, "verifier": verifier, "next": next_url, "at": now}
        return state, verifier

    def take(self, state: str, provider: str) -> dict:
        with self._lock:
            entry = self._s.pop(state or "", None)
        if not entry or entry["provider"] != provider or entry["at"] < time.time() - STATE_TTL:
            raise OAuthError("this sign-in link expired; try again")
        return entry


def _challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


_discovery: dict | None = None


def _google() -> dict:
    global _discovery
    if _discovery is None:
        r = httpx.get(GOOGLE_DISCOVERY, timeout=10)
        r.raise_for_status()
        _discovery = r.json()
    return _discovery


def authorize_url(provider: str, redirect_uri: str, state: str, verifier: str) -> str:
    client_id, _ = _creds(provider)
    if provider == "github":
        q = {"client_id": client_id, "redirect_uri": redirect_uri, "scope": "read:user user:email", "state": state,
             "code_challenge": _challenge(verifier), "code_challenge_method": "S256", "allow_signup": "true"}
        return f"{GITHUB_AUTHORIZE}?{urlencode(q)}"
    if provider == "google":
        q = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "scope": "openid email profile",
             "state": state, "prompt": "select_account"}
        return f"{_google()['authorization_endpoint']}?{urlencode(q)}"
    raise OAuthError(f"unknown provider {provider}")


def _token(r: httpx.Response) -> str:
    try:
        body = r.json()
    except ValueError:
        body = {}
    if r.status_code >= 400 or "access_token" not in body:
        raise OAuthError(f"the provider refused the sign-in ({body.get('error_description') or body.get('error') or r.status_code})")
    return body["access_token"]


def identity(provider: str, code: str, redirect_uri: str, verifier: str) -> Identity:
    client_id, secret = _creds(provider)
    with httpx.Client(timeout=15) as http:
        if provider == "github":
            token = _token(http.post(GITHUB_TOKEN, headers={"Accept": "application/json"}, data={
                "client_id": client_id, "client_secret": secret, "code": code, "redirect_uri": redirect_uri, "code_verifier": verifier}))
            auth = {**GITHUB_HEADERS, "Authorization": f"Bearer {token}"}
            u = http.get(f"{GITHUB_API}/user", headers=auth)
            u.raise_for_status()
            user = u.json()
            e = http.get(f"{GITHUB_API}/user/emails", headers=auth)
            emails = e.json() if e.status_code == 200 else []
            best = next((m for m in emails if m.get("primary") and m.get("verified")), None) or next((m for m in emails if m.get("verified")), None)
            return Identity("github", str(user["id"]), best["email"] if best else None, bool(best), user.get("name") or user.get("login"), user.get("avatar_url"))
        if provider == "google":
            d = _google()
            token = _token(http.post(d["token_endpoint"], data={
                "code": code, "client_id": client_id, "client_secret": secret, "redirect_uri": redirect_uri, "grant_type": "authorization_code"}))
            u = http.get(d["userinfo_endpoint"], headers={"Authorization": f"Bearer {token}"})
            u.raise_for_status()
            info = u.json()
            verified = info.get("email_verified") in (True, "true")  # the docs show both forms
            return Identity("google", str(info["sub"]), info.get("email"), verified, info.get("name"), info.get("picture"))
    raise OAuthError(f"unknown provider {provider}")

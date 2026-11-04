"""Accounts: email and password, GitHub and Google sign-in, sessions and access tokens.

Everything lives in one SQLite file next to the runs (out/accounts.db). Passwords are hashed
with scrypt; session cookies and access tokens are random and stored only as SHA-256 hashes,
so a copy of the database cannot be used to sign in.

Access tokens ("rsn_...") are for the CLI and scripts: send them as
`Authorization: Bearer rsn_...`. The first account created is the admin, who sees every run
and the whole cost ledger.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path

SESSION_DAYS = 30
TOKEN_PREFIX = "rsn_"
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8
PROVIDER_NAMES = {"github": "GitHub", "google": "Google"}

SCHEMA = """
create table if not exists users (
    id text primary key,
    email text unique not null,
    name text,
    avatar text,
    password text,              -- scrypt$n$r$p$salt$hash, null for sign-in-with-provider only
    email_verified integer not null default 0,
    admin integer not null default 0,
    created real not null
);
create table if not exists identities (
    provider text not null,
    subject text not null,
    user_id text not null references users(id),
    primary key (provider, subject)
);
create table if not exists sessions (
    hash text primary key,
    user_id text not null references users(id),
    created real not null,
    expires real not null
);
create table if not exists tokens (
    id text primary key,
    hash text unique not null,
    user_id text not null references users(id),
    name text not null,
    hint text not null,         -- first characters, to tell tokens apart in a list
    created real not null,
    last_used real
);
create table if not exists run_owners (
    run text primary key,
    user_id text not null references users(id)
);
create table if not exists usage (
    user_id text not null,
    day text not null,          -- YYYY-MM-DD, server local time
    kind text not null,         -- analysis | diagnosis
    n integer not null default 0,
    primary key (user_id, day, kind)
);
"""


class AuthError(Exception):
    """A sign-in or sign-up the user can fix (wrong password, email taken...)."""


def _sha(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    n, r, p = 2**14, 8, 1
    h = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, dklen=32)
    return f"scrypt${n}${r}${p}${salt.hex()}${h.hex()}"


def check_password(password: str, stored: str | None) -> bool:
    try:
        _, n, r, p, salt, h = (stored or "").split("$")
        got = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=32)
    except ValueError:
        return False
    return hmac.compare_digest(got.hex(), h)


def public(user: dict) -> dict:
    """What the browser and the CLI may see about an account."""
    return {k: user[k] for k in ("id", "email", "name", "avatar", "admin")} | {"has_password": bool(user.get("password"))}


class Accounts:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.executescript(SCHEMA)
        self._failures: dict[str, list[float]] = {}

    def _q(self, sql: str, args: tuple = ()) -> list[dict]:
        with self._lock:
            cur = self._db.execute(sql, args)
            rows = [dict(r) for r in cur.fetchall()]
            self._db.commit()
            return rows

    def _one(self, sql: str, args: tuple = ()) -> dict | None:
        rows = self._q(sql, args)
        return rows[0] if rows else None

    # ---- users ----
    def user(self, user_id: str) -> dict | None:
        return self._one("select * from users where id = ?", (user_id,))

    def by_email(self, email: str) -> dict | None:
        return self._one("select * from users where email = ?", (email.strip().lower(),))

    def _create(self, email: str, name: str | None, password: str | None, avatar: str | None, verified: bool) -> dict:
        email = email.strip().lower()
        if not EMAIL.match(email):
            raise AuthError("enter a valid email address")
        first = self._one("select count(*) as n from users")["n"] == 0
        uid = secrets.token_hex(8)
        try:
            self._q(
                "insert into users (id, email, name, avatar, password, email_verified, admin, created) values (?, ?, ?, ?, ?, ?, ?, ?)",
                (uid, email, (name or "").strip() or email.split("@")[0], avatar, password, int(verified), int(first), time.time()),
            )
        except sqlite3.IntegrityError:
            raise AuthError("an account with this email already exists; sign in instead") from None
        return self.user(uid)

    def sign_up(self, email: str, password: str, name: str | None = None) -> dict:
        if len(password or "") < MIN_PASSWORD:
            raise AuthError(f"use a password of at least {MIN_PASSWORD} characters")
        return self._create(email, name, hash_password(password), None, verified=False)

    def sign_in(self, email: str, password: str) -> dict:
        key = (email or "").strip().lower()
        now = time.time()
        recent = [t for t in self._failures.get(key, []) if now - t < 600]
        if len(recent) >= 5:
            raise AuthError("too many wrong passwords; wait 10 minutes and try again")
        user = self.by_email(key)
        if not user or not check_password(password or "", user["password"]):
            if len(self._failures) > 10000:  # forget stale entries, so made-up emails cannot pile up
                self._failures = {k: v for k, v in self._failures.items() if now - v[-1] < 600}
            self._failures[key] = [*recent, now]
            if user and not user["password"]:
                raise AuthError("this account signs in with GitHub or Google")
            raise AuthError("wrong email or password")
        self._failures.pop(key, None)
        return user

    def sign_in_with(self, provider: str, subject: str, email: str | None, verified: bool, name: str | None, avatar: str | None) -> dict:
        """The account for a provider identity: the one already linked, else the account with
        the same verified email, else a new one."""
        link = self._one("select user_id from identities where provider = ? and subject = ?", (provider, subject))
        if link:
            return self.user(link["user_id"])
        if not email or not verified:
            raise AuthError(f"your {PROVIDER_NAMES.get(provider, provider)} account has no verified email address")
        user = self.by_email(email)
        if user is None:
            user = self._create(email, name, None, avatar, verified=True)
        elif not user["email_verified"]:
            # Someone signed up with this email and a password but never proved they own it;
            # the provider just proved this person does. Drop that password and its sessions so
            # an account pre-registered by someone else cannot be shared.
            self._q("update users set password = null, email_verified = 1 where id = ?", (user["id"],))
            self._q("delete from sessions where user_id = ?", (user["id"],))
            self._q("delete from tokens where user_id = ?", (user["id"],))
        if avatar and not user.get("avatar"):
            self._q("update users set avatar = ? where id = ?", (avatar, user["id"]))
        self._q("insert into identities (provider, subject, user_id) values (?, ?, ?)", (provider, subject, user["id"]))
        return self.user(user["id"])

    def delete_user(self, user_id: str) -> list[str]:
        """Erase the account and everything that signs in as it; returns the runs it owned."""
        runs = [r["run"] for r in self._q("select run from run_owners where user_id = ?", (user_id,))]
        for table in ("run_owners", "tokens", "sessions", "identities", "usage"):
            self._q(f"delete from {table} where user_id = ?", (user_id,))
        self._q("delete from users where id = ?", (user_id,))
        return runs

    def providers(self, user_id: str) -> list[str]:
        return [r["provider"] for r in self._q("select provider from identities where user_id = ?", (user_id,))]

    # ---- sessions (browser cookie) ----
    def new_session(self, user_id: str) -> str:
        raw = secrets.token_urlsafe(32)
        now = time.time()
        self._q("insert into sessions (hash, user_id, created, expires) values (?, ?, ?, ?)", (_sha(raw), user_id, now, now + SESSION_DAYS * 86400))
        return raw

    def session_user(self, raw: str | None) -> dict | None:
        if not raw:
            return None
        row = self._one("select user_id, expires from sessions where hash = ?", (_sha(raw),))
        if not row or row["expires"] < time.time():
            return None
        return self.user(row["user_id"])

    def end_session(self, raw: str | None) -> None:
        if raw:
            self._q("delete from sessions where hash = ?", (_sha(raw),))

    # ---- access tokens (CLI and scripts) ----
    def new_token(self, user_id: str, name: str) -> tuple[str, dict]:
        raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
        tid = secrets.token_hex(6)
        self._q(
            "insert into tokens (id, hash, user_id, name, hint, created) values (?, ?, ?, ?, ?, ?)",
            (tid, _sha(raw), user_id, (name or "token").strip()[:60] or "token", raw[:8], time.time()),
        )
        return raw, self._token_row(tid)

    def _token_row(self, tid: str) -> dict:
        return self._one("select id, name, hint, created, last_used from tokens where id = ?", (tid,))

    def tokens(self, user_id: str) -> list[dict]:
        return self._q("select id, name, hint, created, last_used from tokens where user_id = ? order by created desc", (user_id,))

    def revoke(self, user_id: str, token_id: str) -> bool:
        before = len(self.tokens(user_id))
        self._q("delete from tokens where id = ? and user_id = ?", (token_id, user_id))
        return len(self.tokens(user_id)) < before

    def token_user(self, raw: str | None) -> dict | None:
        if not raw or not raw.startswith(TOKEN_PREFIX):
            return None
        row = self._one("select id, user_id from tokens where hash = ?", (_sha(raw),))
        if not row:
            return None
        self._q("update tokens set last_used = ? where id = ?", (time.time(), row["id"]))
        return self.user(row["user_id"])

    # ---- daily usage (spend caps on paid model calls) ----
    def used_today(self, user_id: str, kind: str) -> int:
        row = self._one("select n from usage where user_id = ? and day = ? and kind = ?", (user_id, time.strftime("%Y-%m-%d"), kind))
        return row["n"] if row else 0

    def count_use(self, user_id: str, kind: str) -> None:
        self._q("insert into usage (user_id, day, kind, n) values (?, ?, ?, 1) on conflict(user_id, day, kind) do update set n = n + 1",
                (user_id, time.strftime("%Y-%m-%d"), kind))

    # ---- run ownership ----
    def set_owner(self, run: str, user_id: str) -> None:
        self._q("insert or replace into run_owners (run, user_id) values (?, ?)", (run, user_id))

    def owners(self) -> dict[str, str]:
        return {r["run"]: r["user_id"] for r in self._q("select run, user_id from run_owners")}


class DeviceLogins:
    """Sign the CLI in through the browser, like `gh auth login`: the CLI shows a short code,
    the signed-in user approves it on the website, and the CLI picks up a fresh token."""

    TTL = 600

    def __init__(self):
        self._pending: dict[str, dict] = {}
        self._lock = threading.Lock()

    def start(self, name: str) -> dict:
        alphabet = "BCDFGHJKLMNPQRSTVWXZ"  # no vowels: no accidental words, no 0/O or 1/I
        user_code = "".join(secrets.choice(alphabet) for _ in range(4)) + "-" + "".join(secrets.choice(alphabet) for _ in range(4))
        device_code = secrets.token_urlsafe(24)
        with self._lock:
            self._expire()
            self._pending[device_code] = {"user_code": user_code, "name": name, "expires": time.time() + self.TTL, "token": None, "user": None}
        return {"device_code": device_code, "user_code": user_code, "expires_in": self.TTL}

    def _expire(self) -> None:
        now = time.time()
        for k in [k for k, v in self._pending.items() if v["expires"] < now]:
            del self._pending[k]

    def lookup(self, user_code: str) -> dict | None:
        with self._lock:
            self._expire()
            return next((v for v in self._pending.values() if v["user_code"] == user_code.strip().upper()), None)

    def approve(self, user_code: str, token: str, user: dict) -> bool:
        with self._lock:
            entry = next((v for v in self._pending.values() if v["user_code"] == user_code.strip().upper() and v["token"] is None), None)
            if entry is None:
                return False
            entry["token"], entry["user"] = token, user
            return True

    def poll(self, device_code: str) -> dict | None:
        """The token once approved (handed out once), {} while waiting, None when unknown or expired."""
        with self._lock:
            self._expire()
            entry = self._pending.get(device_code)
            if entry is None:
                return None
            if entry["token"] is None:
                return {}
            del self._pending[device_code]
            return {"token": entry["token"], "user": entry["user"]}

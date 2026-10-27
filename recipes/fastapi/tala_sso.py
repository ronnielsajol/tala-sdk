"""TALA SSO for FastAPI (and any asyncio Python backend).

Copy this file into your project. It mirrors the behaviour of the `tala/sso-laravel` package
v1.1: single-use `state`, PKCE (S256), team allow-list, and `id` as the stable subject.

Dependencies: fastapi, httpx.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx

log = logging.getLogger("tala_sso")


class TalaAuthError(Exception):
    """An error whose message is safe to show to the browser."""

    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class StateStore(Protocol):
    async def put(self, key: str, value: dict, ttl: int) -> None: ...

    async def pop(self, key: str) -> dict | None:
        """Return and delete the value, or None if missing or expired. Must be atomic."""
        ...


class MemoryStateStore:
    """Single-process only. With several workers or servers use a shared store such as Redis
    (`put` = SET key value EX ttl, `pop` = GETDEL)."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[float, dict]] = {}

    async def put(self, key: str, value: dict, ttl: int) -> None:
        now = time.monotonic()
        self._data = {k: v for k, v in self._data.items() if v[0] > now}
        self._data[key] = (now + ttl, value)

    async def pop(self, key: str) -> dict | None:
        item = self._data.pop(key, None)
        if item is None or item[0] <= time.monotonic():
            return None
        return item[1]


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


@dataclass
class TalaConfig:
    base_url: str
    client_id: str
    client_secret: str
    redirect_uri: str
    allowed_teams: list[str] = field(default_factory=list)
    pkce: bool = True
    verify_state: bool = True
    state_ttl: int = 600


class TalaSSO:
    def __init__(self, config: TalaConfig, store: StateStore, http: httpx.AsyncClient | None = None) -> None:
        self.cfg = config
        self.base = config.base_url.rstrip("/")
        self.store = store
        self.http = http or httpx.AsyncClient(timeout=10)

    @staticmethod
    def _key(state: str) -> str:
        return "tala-sso:state:" + hashlib.sha256(state.encode()).hexdigest()

    async def redirect(self) -> dict[str, str]:
        state = secrets.token_urlsafe(30)
        params = {
            "client_id": self.cfg.client_id,
            "redirect_uri": self.cfg.redirect_uri,
            "response_type": "code",
            "scope": "",
            "state": state,
        }
        verifier = None
        if self.cfg.pkce:
            verifier = _b64url(secrets.token_bytes(48))
            params["code_challenge"] = _b64url(hashlib.sha256(verifier.encode()).digest())
            params["code_challenge_method"] = "S256"
        await self.store.put(self._key(state), {"verifier": verifier}, self.cfg.state_ttl)
        return {"authorize_url": f"{self.base}/oauth/authorize?{urlencode(params)}", "state": state}

    async def _consume_state(self, state: str | None) -> dict:
        if not self.cfg.verify_state:
            return {}
        if not state:
            raise TalaAuthError("Sign-in session is missing or expired. Please try again.", 422)
        context = await self.store.pop(self._key(state))
        if context is None:
            raise TalaAuthError("Sign-in session is missing or expired. Please try again.", 422)
        return context

    async def user_from_callback(self, code: str | None, state: str | None) -> dict[str, Any]:
        if not code:
            raise TalaAuthError("Authorization code is missing from the request.", 422)
        context = await self._consume_state(state)

        payload = {
            "grant_type": "authorization_code",
            "client_id": self.cfg.client_id,
            "client_secret": self.cfg.client_secret,
            "redirect_uri": self.cfg.redirect_uri,
            "code": code,
        }
        if context.get("verifier"):
            payload["code_verifier"] = context["verifier"]

        token = await self.http.post(f"{self.base}/oauth/token", data=payload)
        if token.is_error:
            log.warning("TALA token exchange failed: %s", token.status_code)
            raise TalaAuthError("Could not complete sign-in with TALA.")
        access_token = token.json().get("access_token")
        if not access_token:
            raise TalaAuthError("Could not complete sign-in with TALA.")

        resp = await self.http.get(f"{self.base}/api/oauth/user", headers={"Authorization": f"Bearer {access_token}"})
        if resp.is_error:
            log.warning("TALA profile fetch failed: %s", resp.status_code)
            raise TalaAuthError("Could not read your TALA profile.")
        profile = resp.json()
        # `id` is TALA's stable subject. Never key local users on email.
        if not isinstance(profile, dict) or not profile.get("id"):
            raise TalaAuthError("Could not read your TALA profile.")

        allowed = [t for t in self.cfg.allowed_teams if t]
        if allowed and profile.get("team") not in allowed:
            raise TalaAuthError("Your TALA account is not permitted to use this application.", 403)

        return {**profile, "oauth_token": access_token}

    async def revoke_token(self, access_token: str) -> bool:
        resp = await self.http.post(
            f"{self.base}/api/oauth/revoke-token", headers={"Authorization": f"Bearer {access_token}"}
        )
        return resp.is_success

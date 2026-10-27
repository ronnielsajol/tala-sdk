import asyncio
import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from tala_sso import MemoryStateStore, TalaAuthError, TalaConfig, TalaSSO


def make(handler, **cfg):
    config = TalaConfig(
        base_url="https://tala.example.com",
        client_id="cid",
        client_secret="secret",
        redirect_uri="https://app.example.com/auth/tala/callback",
        **cfg,
    )
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TalaSSO(config, MemoryStateStore(), http)


def ok_handler(profile):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/token":
            seen["token_form"] = parse_qs(request.content.decode())
            return httpx.Response(200, json={"access_token": "tok"})
        if request.url.path == "/api/oauth/user":
            return httpx.Response(200, json=profile)
        return httpx.Response(204)

    handler.seen = seen
    return handler


def run(coro):
    return asyncio.run(coro)


def test_redirect_has_state_and_s256_challenge():
    out = run(make(ok_handler({"id": 1})).redirect())
    q = parse_qs(urlparse(out["authorize_url"]).query)
    assert q["state"] == [out["state"]]
    assert q["code_challenge_method"] == ["S256"]


def test_full_flow_sends_matching_verifier_and_state_is_single_use():
    handler = ok_handler({"id": 7, "email": "a@b.c", "team": "x"})
    sso = make(handler)

    async def go():
        out = await sso.redirect()
        challenge = parse_qs(urlparse(out["authorize_url"]).query)["code_challenge"][0]
        user = await sso.user_from_callback("code1", out["state"])
        verifier = handler.seen["token_form"]["code_verifier"][0]
        digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        assert digest == challenge
        assert user["id"] == 7 and user["oauth_token"] == "tok"
        with pytest.raises(TalaAuthError):
            await sso.user_from_callback("code1", out["state"])

    run(go())


def test_unknown_state_rejected():
    with pytest.raises(TalaAuthError) as e:
        run(make(ok_handler({"id": 1})).user_from_callback("c", "nope"))
    assert e.value.status_code == 422


def test_missing_id_rejected():
    sso = make(ok_handler({"email": "a@b.c"}))

    async def go():
        out = await sso.redirect()
        await sso.user_from_callback("c", out["state"])

    with pytest.raises(TalaAuthError):
        run(go())


@pytest.mark.parametrize(
    "profile,ok",
    [({"id": 1, "team": "a"}, True), ({"id": 1, "team": "b"}, False), ({"id": 1}, False)],
)
def test_team_allow_list(profile, ok):
    sso = make(ok_handler(profile), allowed_teams=["a"])

    async def go():
        out = await sso.redirect()
        return await sso.user_from_callback("c", out["state"])

    if ok:
        assert run(go())["id"] == 1
    else:
        with pytest.raises(TalaAuthError) as e:
            run(go())
        assert e.value.status_code == 403

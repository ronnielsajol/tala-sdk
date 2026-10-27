"""Wiring example. Adapt `login_handler` to your user model and session/JWT scheme."""
import os

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from tala_sso import MemoryStateStore, TalaAuthError, TalaConfig, TalaSSO

sso = TalaSSO(
    TalaConfig(
        base_url=os.environ["TALA_OAUTH_BASE_URL"],
        client_id=os.environ["TALA_OAUTH_CLIENT_ID"],
        client_secret=os.environ["TALA_OAUTH_CLIENT_SECRET"],
        redirect_uri=os.environ["TALA_OAUTH_REDIRECT_URI"],
        allowed_teams=os.environ.get("TALA_ALLOWED_TEAMS", "").split(","),
    ),
    store=MemoryStateStore(),  # use a shared (Redis) store with more than one worker
)


async def login_handler(tala_user: dict) -> dict:
    # 1. Look up the local user by tala_user["id"] (never by email); create it on first login.
    # 2. Keep tala_user["oauth_token"] if you want to revoke it at logout.
    # 3. Issue your own session token / JWT and return what the frontend needs.
    raise NotImplementedError


router = APIRouter(prefix="/api/auth/tala")


@router.get("/redirect")
async def redirect():
    return await sso.redirect()


@router.post("/callback")
async def callback(request: Request):
    body = await request.json()
    try:
        tala_user = await sso.user_from_callback(body.get("code"), body.get("state"))
        data = await login_handler(tala_user)
    except TalaAuthError as exc:
        return JSONResponse({"success": False, "error": exc.message}, status_code=exc.status_code)
    except Exception:
        # Log it in your app; the browser only sees a generic message.
        return JSONResponse({"success": False, "error": "Authentication failed."}, status_code=401)
    return {"success": True, "data": data}


app = FastAPI()
app.include_router(router)

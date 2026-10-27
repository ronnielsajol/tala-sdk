# TALA SSO for FastAPI

A copy-in module (no package to install) that does what `tala/sso-laravel` v1.1 does: single-use
`state`, PKCE (S256), a team allow-list, and TALA's `id` as the stable user key.

| File | Purpose |
| --- | --- |
| `tala_sso.py` | The module. Copy it into your project. |
| `example_app.py` | Router with `GET /api/auth/tala/redirect` and `POST /api/auth/tala/callback`. |
| `test_tala_sso.py` | Tests for the module (`pip install pytest`, then `pytest`). |

These routes match the ones the `@tala/sso-react` button expects, so the frontend is unchanged.

## Steps

1. `pip install fastapi httpx`, copy `tala_sso.py` into your project.
2. Set the environment variables used in `example_app.py`: `TALA_OAUTH_BASE_URL`,
   `TALA_OAUTH_CLIENT_ID`, `TALA_OAUTH_CLIENT_SECRET`, `TALA_OAUTH_REDIRECT_URI`, and optionally
   `TALA_ALLOWED_TEAMS` (comma-separated). The redirect URI is your frontend callback page and
   must match the client registered in TALA exactly.
3. Implement `login_handler` for your user model. Find or create the local user by
   `tala_user["id"]`, never by email. Issue your own session token and return what the frontend
   needs. Throw `TalaAuthError("message", status)` for messages that are safe to show; any other
   exception is shown as "Authentication failed."
4. Use a shared state store if you run more than one worker or server. `MemoryStateStore` is for
   a single process only. A Redis store needs `put` (`SET key value EX ttl`, value as JSON) and an
   atomic `pop` (`GETDEL`).
5. For logout, keep `tala_user["oauth_token"]` for the user and call `sso.revoke_token(token)`
   before deleting the local session.

## Notes

- Do not commit the client secret. Keep it in the environment.
- `TalaAuthError` messages are returned to the browser; everything else should be logged only.
- Written against the contract documented in the integration guide. It has been tested with a mock
  transport, not yet against a real TALA server or the Python project.

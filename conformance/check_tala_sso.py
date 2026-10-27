#!/usr/bin/env python3
"""Black-box conformance check for an app's TALA SSO backend endpoints.

Usage:
    python check_tala_sso.py https://api.your-app.example.com
    python check_tala_sso.py http://localhost:8000 --prefix /api/auth/tala

It only uses the standard library and never completes a login. It calls the app's
`GET <prefix>/redirect` and sends bogus requests to `POST <prefix>/callback`, then checks the
responses against the TALA SSO contract. It cannot see inside the app, so it does not prove
the profile checks (`id`, `team`, allow-list) or logout; those stay on the checklist in
skills/tala-sso/SKILL.md.

Exit code 0 when every check passes, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

results: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    results.append((ok, name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail and not ok else ""))


def call(method: str, url: str, body: dict | None = None) -> tuple[int, str]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def leaks_internals(text: str) -> bool:
    markers = ("Traceback", "Stack trace", "vendor/", ".php", "site-packages", "SQLSTATE", "at Object.", "node_modules")
    return any(m in text for m in markers)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base_url", help="Backend base URL, e.g. https://api.example.com")
    ap.add_argument("--prefix", default="/api/auth/tala", help="Route prefix (default /api/auth/tala)")
    args = ap.parse_args()
    base = args.base_url.rstrip("/") + args.prefix

    # 1. redirect
    status, text = call("GET", base + "/redirect")
    check(status == 200, "redirect returns 200", f"got {status}")
    try:
        first = json.loads(text)
        payload = first.get("data", first) if isinstance(first, dict) else {}
    except json.JSONDecodeError:
        payload = {}
    authorize_url = payload.get("authorize_url", "")
    state = payload.get("state", "")
    check(bool(authorize_url and state), "redirect returns authorize_url and state", text[:120])

    q = urllib.parse.parse_qs(urllib.parse.urlparse(authorize_url).query)
    path = urllib.parse.urlparse(authorize_url).path
    check(path.endswith("/oauth/authorize"), "authorize_url points at /oauth/authorize", path)
    check(q.get("response_type") == ["code"], "response_type=code")
    check(bool(q.get("client_id")), "client_id present")
    check(bool(q.get("redirect_uri")), "redirect_uri present")
    check(q.get("state") == [state] and bool(state), "state in URL matches returned state")
    check(len(state) >= 32, "state has at least 32 characters (unguessable)", f"length {len(state)}")
    check(q.get("code_challenge_method") == ["S256"], "PKCE: code_challenge_method=S256")
    check(len(q.get("code_challenge", [""])[0]) >= 43, "PKCE: code_challenge present (43+ chars)")
    check(urllib.parse.urlparse(authorize_url).scheme == "https" or "localhost" in authorize_url,
          "authorize_url uses https (or localhost)")

    # 2. state is unique per login
    _, text2 = call("GET", base + "/redirect")
    try:
        second = json.loads(text2)
        state2 = (second.get("data", second) if isinstance(second, dict) else {}).get("state", "")
    except json.JSONDecodeError:
        state2 = ""
    check(bool(state2) and state2 != state, "each redirect issues a new state")

    # 3. callback rejects bad input without leaking internals
    bad_cases = [
        ("unknown state", {"code": "bogus", "state": "not-a-real-state-" + "x" * 30}),
        ("missing state", {"code": "bogus"}),
        ("missing code", {"state": state}),
        ("empty body", {}),
    ]
    for label, body in bad_cases:
        status, text = call("POST", base + "/callback", body)
        check(400 <= status < 500, f"callback rejects {label} with a 4xx", f"got {status}")
        check(not leaks_internals(text), f"callback error for {label} does not leak internals", text[:120])
        check('"token"' not in text and "access_token" not in text, f"callback for {label} returns no token")

    # 4. state is not reusable after a failed attempt with it
    status, _ = call("POST", base + "/callback", {"code": "bogus", "state": state})
    status_again, _ = call("POST", base + "/callback", {"code": "bogus", "state": state})
    check(400 <= status_again < 500, "reusing a state is rejected", f"got {status_again}")

    failed = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

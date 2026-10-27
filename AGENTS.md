# Instructions for AI coding agents

This repo documents how to add TALA single sign-on (SSO) to a project.

## Adding or reviewing TALA SSO in a project

Follow `skills/tala-sso/SKILL.md`. It detects the stack (Laravel, React/Next.js, FastAPI), says
what to install, and ends with a contract checklist. Do not write OAuth code from scratch.

Then read, as needed:

- `tala_sso_integration_guide.md`: the contract, Laravel backend and React frontend setup.
- `recipes/fastapi/`: copy-in module for FastAPI backends.
- `private-repo-access.md`: SSH access to the private SDK repos (`sso-laravel`, `sso-react`).
- `conformance/check_tala_sso.py`: black-box check of a running backend. Run it before finishing:
  `python conformance/check_tala_sso.py <backend-base-url>`.

## Rules

- Never commit or print client secrets, tokens, `.env` files or real hostnames. Docs here use
  placeholders such as `https://tala.example.com` and `<owner>`.
- Key local users on TALA's `id`, never on email.
- Do not push, deploy or run migrations on production without the user's explicit approval.
- The SDK repos are private. If you cannot install them (no SSH access), stop and tell the user;
  do not copy the SDK source from elsewhere.
- If the project's stack has no recipe (for example Django, Flask or Node), say so instead of improvising.

## Working in this repo

- Documentation and examples only; keep it free of secrets and real hostnames because it is public.
- FastAPI recipe tests: `pip install fastapi httpx pytest`, then `pytest` inside `recipes/fastapi`.
- `sso-laravel/` and `sso-react/` here are separate repositories and are git-ignored.

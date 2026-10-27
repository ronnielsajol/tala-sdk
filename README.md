# TALA SDK docs

Documentation for adding TALA single sign-on to a project.

| Document | What it is for |
| --- | --- |
| [tala_sso_integration_guide.md](tala_sso_integration_guide.md) | How to integrate TALA SSO: Laravel backend, React frontend, security settings, logout. |
| [private-repo-access.md](private-repo-access.md) | How to get read access to the private SDK repos with an SSH key, including servers and GitHub Actions. |
| [recipes/fastapi](recipes/fastapi/README.md) | Copy-in TALA SSO module for FastAPI backends, with tests. |
| [skills/tala-sso/SKILL.md](skills/tala-sso/SKILL.md) | Agent skill: detect the stack, apply the SDK or recipe, run the contract checklist. |

## The SDK repositories (private)

- `sso-laravel`: Composer package `tala/sso-laravel` (latest release v1.1.0).
- `sso-react`: npm package `@tala/sso-react`.

This repo holds documentation only. Keep it free of client IDs, client secrets, `.env` files and
real hostnames; use placeholders such as `https://tala.example.com`.

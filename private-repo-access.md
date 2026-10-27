# Getting access to the private TALA SDK repos (SSH)

The TALA SDK repos are private. To install them with Composer or npm, a developer needs
(1) read access to the repos and (2) an SSH key registered on their GitHub account.

Repos (owner placeholder: `<owner>`):

- `<owner>/sso-laravel` (Composer package `tala/sso-laravel`)
- `<owner>/sso-react` (npm package `@tala/sso-react`)

## How SSH keys work (read this first)

An SSH key is a **pair of files**, made on one specific device:

| File | What it is | Where it lives |
| --- | --- | --- |
| `id_ed25519` (private key) | Your proof of identity. Like a house key. | **Only on the device that made it.** Never copied, emailed or committed. |
| `id_ed25519.pub` (public key) | The matching lock. Safe to share. | Pasted into GitHub. |

GitHub stores the public key. When a device runs `git clone` or `composer install`, GitHub
asks "prove you hold the private key for one of the public keys I know." If it does, and that
key's owner has read access to the repo, GitHub lets it in. No password is ever sent.

So the rule is **one key per device**, and each key gets a **device name** so you can tell them
apart (and delete just one if a device is lost):

| Device | Example `<device-name>` | Where the private key lives |
| --- | --- | --- |
| Your work laptop | `ronniel-laptop` | The laptop's `~/.ssh/` |
| A second computer | `ronniel-desktop` | That computer's `~/.ssh/` |
| Production server | `deploy-ask-nest-prod` | The server's `~/.ssh/` |
| GitHub Actions CI | `ci-ask-nest-tests` | CI secret store |

Everywhere below, `<device-name>` means the name of the device you are **sitting at while you
run the command**. Do the steps once per device. A key made on your laptop does not give your
server access, and the server needs its own.

In the GitHub **SSH keys** list you will see one row per device, titled with that name. For
servers and CI, use a **deploy key** (section D) tied to one repo, not your personal key.

## A. For the repo owner: give someone access

1. GitHub → the repo → **Settings** → **Collaborators** → **Add people**.
2. Enter the developer's GitHub username and choose the **Read** role.
3. The developer accepts the emailed invitation. Repeat for each repo.

For CI/CD servers, use a **deploy key** instead of a personal key (section D).

## B. For each developer: create and register an SSH key

Run these in Git Bash or PowerShell (Windows 10/11 includes OpenSSH).

1. Check for an existing key. If `~/.ssh/id_ed25519.pub` exists, you can reuse it and skip to step 3.
   ```bash
   ls ~/.ssh
   ```
2. Create a key for **this device**. Put the device name in the comment (`-C`) so you can
   recognize it later. Use a passphrase.
   ```bash
   ssh-keygen -t ed25519 -C "<your-name>@<device-name>"
   ```
   Example: `ssh-keygen -t ed25519 -C "ronniel@ronniel-laptop"`. Press Enter to accept the
   default path (if a key already exists there, choose a new file name such as
   `~/.ssh/id_ed25519_<device-name>` so you do not overwrite it).
3. Start the SSH agent and add the key.
   - Git Bash / macOS / Linux:
     ```bash
     eval "$(ssh-agent -s)"
     ssh-add ~/.ssh/id_ed25519
     ```
   - Windows PowerShell (run once as Administrator, then normal shell):
     ```powershell
     Set-Service ssh-agent -StartupType Automatic
     Start-Service ssh-agent
     ssh-add $env:USERPROFILE\.ssh\id_ed25519
     ```
4. Copy the **public** key (the `.pub` file). Never share the file without `.pub`.
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
5. GitHub → profile photo → **Settings** → **SSH and GPG keys** → **New SSH key**. Give it a
   title (use `<device-name>`, e.g. `ronniel-laptop`), type **Authentication Key**, paste the
   key, save.
6. Test the connection. The first time, type `yes` to trust GitHub's host.
   ```bash
   ssh -T git@github.com
   ```
   Expected: `Hi <username>! You've successfully authenticated, but GitHub does not provide shell access.`
7. Test repo access (after the owner added you):
   ```bash
   git ls-remote git@github.com:<owner>/sso-laravel.git
   ```
   A list of refs means it works. `Repository not found` means you have not accepted the
   invitation or were not added.

### If you have several keys on one device

SSH tries your keys in turn, and you may have others (e.g. for a hosting provider). Tell it
which key GitHub should use by adding this to `~/.ssh/config` (create the file if needed):
```
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github
    IdentitiesOnly yes
```
Use the file name you chose in step 2. Never overwrite a key that another service already
uses; make a new file for GitHub instead.

## C. Install the SDKs over SSH

**Laravel**: in the app's `composer.json`:
```json
"repositories": [
    { "type": "vcs", "url": "git@github.com:<owner>/sso-laravel.git" }
]
```
```bash
composer require tala/sso-laravel
```
Composer uses your SSH key automatically. Make sure the agent is running, or Composer will
prompt for the key passphrase.

**React**: pin a tag so installs are repeatable:
```bash
npm install "git+ssh://git@github.com/<owner>/sso-react.git#v1.1.0"
```
The package builds itself on install (`prepare` script), so Node and npm must be able to run
`tsup` (installed as a dev dependency automatically).

## D. Servers and GitHub Actions (deploy keys, not personal keys)

**What "CI" means here:** CI is any automatic job that runs `composer install` without you
sitting at it. In your projects that is **GitHub Actions**, the workflow files in
`.github/workflows/`. Two different machines run `composer install`, and each needs its own key:

| Machine | Which workflow | What it does | Where the key goes |
| --- | --- | --- | --- |
| **Your server** (e.g. Hostinger) | `pull-changes.yml` | GitHub logs in to the server over SSH (using the `PROD_SSH_KEY` secret), and the **server** runs `git fetch` and `composer install`. | On the server, in `~/.ssh/`. |
| **GitHub's test machine** | `tests.yml` | A temporary Ubuntu machine from GitHub checks out the code and runs `composer install` before the tests. | In the repo's **Settings → Secrets and variables → Actions**, loaded with the `webfactory/ssh-agent` step (the deploy workflow already uses it). |

In both cases the machine downloads `sso-laravel` from GitHub. Once that repo is private, the
machine must prove who it is, the same way your laptop does. Never copy your personal key onto
a server or into a secret. Make a **deploy key**: a key that can read **one repo** and nothing else.

**Important limit:** a given key can be a deploy key on **only one repo** (a repo can have
several deploy keys, but each key belongs to one repo). The server already has a deploy key for
the app repo (`pull-changes.yml` says so), so it needs a **second, different** key for
`sso-laravel`. Because SSH would normally offer only
one key to `github.com`, the second key is given an alias (this is why `INSIGHT` has
`github.com-sso-laravel`).

### D1. Server (Hostinger and similar)

1. Log in to the server and create a key for `sso-laravel` only:
   ```bash
   ssh-keygen -t ed25519 -C "<device-name>" -f ~/.ssh/sso_laravel_deploy -N ""
   ```
   Example `<device-name>`: `deploy-ask-nest-prod`. The private key stays on the server.
2. Show the public key and copy it: `cat ~/.ssh/sso_laravel_deploy.pub`
3. GitHub → **`sso-laravel`** → **Settings → Deploy keys → Add deploy key**. Title it with
   `<device-name>`, paste the key, leave **Allow write access** unchecked.
4. On the server, add to `~/.ssh/config`:
   ```
   Host github.com-sso-laravel
       HostName github.com
       User git
       IdentityFile ~/.ssh/sso_laravel_deploy
       IdentitiesOnly yes
   ```
5. In that app's `composer.json`, the repository URL must use the alias:
   `git@github.com-sso-laravel:ronnielsajol/sso-laravel.git`
   (the alias lets the server pick the right key; your laptop needs the same alias or a
   `Host github.com-sso-laravel` entry in its own `~/.ssh/config`).
6. Test on the server: `ssh -T git@github.com-sso-laravel`

Do this once **per server**, not per app. If several apps run on the same server (for example
`ask-nest`, `timeline-app` and `survey-asc` on one host), they all share this one key and alias,
as long as each app's `composer.json` uses the alias URL from step 5.

**GitHub Actions caveat:** the alias only exists where you create it. On GitHub's test machine
(D2) it does not, so a `composer.json` with `git@github.com-sso-laravel:` fails there. Add this
step to `tests.yml`, after the ssh-agent step and before `composer install`, to map the alias
back to the real host:
```yaml
- run: git config --global url."git@github.com:".insteadOf "git@github.com-sso-laravel:"
```

### D2. GitHub Actions test runs (`tests.yml`)

1. On your own computer, create a throwaway key: `ssh-keygen -t ed25519 -C "ci-<repo>-tests" -f ./ci_sso_laravel -N ""`
2. Add `ci_sso_laravel.pub` as a deploy key on **`sso-laravel`** (same steps as D1.3).
3. In the app repo: **Settings → Secrets and variables → Actions → New repository secret**,
   name it `SSO_LARAVEL_KEY`, paste the contents of the **private** file `ci_sso_laravel`.
4. Delete both local files afterward. In `tests.yml`, before `composer install`, add:
   ```yaml
   - uses: webfactory/ssh-agent@v0.9.0
     with:
       ssh-private-key: ${{ secrets.SSO_LARAVEL_KEY }}
   ```
5. Pull requests from forks do not receive secrets, so those runs cannot install the package.

The same private key can be saved as a secret in several app repos, since its public half is
registered only once, on `sso-laravel`. If juggling deploy keys and aliases is too much, a
single key on a dedicated GitHub "machine user" account with read access to the SDK repos is
the usual shortcut; then every server and workflow can use the plain `git@github.com:` URL.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Permission denied (publickey)` | Key not added to the agent (`ssh-add -l` to check) or not registered on GitHub. |
| `Repository not found` | Not invited, invite not accepted, or wrong owner/name. |
| `Host key verification failed` | Run `ssh -T git@github.com` and accept the host fingerprint. |
| Composer asks for GitHub token | The `url` in `composer.json` is HTTPS; change it to the `git@github.com:` form. |
| Key works in Git Bash but not PowerShell | Different agents. Run `ssh-add` in the shell you are using. |

## Security notes

- Keep the private key file (no `.pub`) on one machine, with a passphrase. If a laptop is lost,
  delete that key in GitHub → **SSH and GPG keys**.
- Remove collaborators when someone leaves a project.
- Never commit client IDs, client secrets or `.env` files to these repos.

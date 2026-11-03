# Get access to the private TALA SDK (10-minute version)

Follow this if someone asked you to install or update `@tala/sso-react` (or `tala/sso-laravel`)
and you get "Permission denied" or "repository not found". Do it once per computer.

You need: a GitHub account, and [Git](https://git-scm.com/downloads) installed.
On Windows, run the commands in **Git Bash** (installed with Git). On Mac or Linux, use Terminal.

---

## Step 1. Ask for access

Send the SDK owner your **GitHub username**. They add you as a collaborator with **Read** access
and GitHub sends you an email.

Open that email and click **Accept invitation**. Until you accept, nothing below will work.

## Step 2. Make a key for this computer

Pick a name for this computer, for example `maria-laptop`, and run (put your name in the quotes):

```bash
ssh-keygen -t ed25519 -C "maria-laptop"
```

Press **Enter** three times (accept the default file and an empty passphrase).

If it says `already exists. Overwrite?`, type **n** and press Enter. You already have a key; skip
to step 3 and use that one.

## Step 3. Copy the public key

```bash
cat ~/.ssh/id_ed25519.pub
```

It prints one line starting with `ssh-ed25519`. Select the whole line and copy it.

> Only the `.pub` file is shared. Never send or paste the file without `.pub`.

## Step 4. Add it to GitHub

1. Go to GitHub, click your picture, then **Settings**.
2. Click **SSH and GPG keys**, then **New SSH key**.
3. Title: the computer name (`maria-laptop`). Key type: **Authentication Key**.
4. Paste the line from step 3, then click **Add SSH key**.

## Step 5. Test it

```bash
ssh -T git@github.com
```

The first time it asks `Are you sure you want to continue connecting?`. Type `yes`.

Success looks like: `Hi <your-username>! You've successfully authenticated, but GitHub does not provide shell access.`

If you see `Permission denied (publickey)`, the key was not added (go back to step 4).

## Step 6. Use it

Download the SDK from the tagged release (replace `<owner>` with the owner's GitHub name and use the
version you were given):

```bash
npm pack "git+ssh://git@github.com/<owner>/sso-react.git#v1.1.1"
```

This creates `tala-sso-react-1.1.1.tgz` in the current folder.

### Updating an app that already uses a tarball

1. Copy the new `.tgz` into the app's main folder (next to `package.json`).
2. Delete the old `tala-sso-react-<old version>.tgz`.
3. In `package.json`, change the `@tala/sso-react` line to `"file:tala-sso-react-1.1.1.tgz"`.
4. Run `npm install`, then `npm run build`. Both should finish without errors.
5. Commit the `.tgz`, `package.json` and `package-lock.json`, and push. If the app deploys on
   Vercel Hobby, push as the account owner so the deploy is allowed.
6. When it is live, try one real sign-in with TALA.

---

## Something went wrong

| You see | Do this |
| --- | --- |
| `Permission denied (publickey)` | The key is not on your GitHub account. Repeat step 4, then step 5. |
| `Repository not found` | The invitation was not accepted, or the owner added a different username. Check your email, then ask the owner. |
| `ssh-keygen: command not found` | Open **Git Bash** (Windows) instead of PowerShell or Command Prompt. |
| `npm pack` hangs | Press Ctrl+C. It is waiting for a password because it is not using SSH; check the URL starts with `git+ssh://git@github.com/`. |
| It works in your terminal but not on a server or CI | Servers and CI need their own key. See [private-repo-access.md](private-repo-access.md) section D. |

Never paste your private key (the file without `.pub`) into chat, email or a repository.

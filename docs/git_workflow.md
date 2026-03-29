# Git Branching & Deployment Workflow

This document outlines the standard professional Git workflow for safely updating the Gmail Triage Agent without breaking production.

## The Golden Rule
**Never work directly on `main`**. `main` must always be stable and deployable. All work happens in isolated feature branches.

## 1. Branch Naming Conventions
Always use descriptive prefixes so it's instantly obvious what a branch is doing:

* `feat/` - Adding new features or capabilities (e.g., `feat/daily-summary-metrics`)
* `bugfix/` - Fixing something broken in the agent (e.g., `bugfix/fallback-taxonomy-error`)
* `chore/` - Maintenance, scripts, or non-user-facing updates (e.g., `chore/add-label-cleanup`)
* `docs/` - Updating documentation or READMEs (e.g., `docs/update-readme`)
* `refactor/` - Restructuring existing code without changing its behavior (e.g., `refactor/worker-loop`)

## 2. The Development Cycle

### Step 1: Create Your Branch
Always start from up-to-date `main`:
```bash
git switch main
git pull origin main
git switch -c feat/my-new-feature
```

### Step 2: Make Small, Frequent Commits
Commit logically related chunks of code as you go, rather than waiting a week to make one massive commit. Good commits tell a story.
```bash
git add src/policy.py
git commit -m "feat: add daily summary logic to policy"

git add src/worker.py
git commit -m "feat: wire up summary logs in the worker"
```

### Step 3: Test Locally
Before pushing anything, run your code locally to ensure it doesn't crash.
```bash
# Run unit tests
python tests/test_truncation.py

# Run the local docker container to verify it boots
docker compose up -d
```

### Step 4: Push and Merge
Once you're happy, push your branch to GitHub.
```bash
git push -u origin feat/my-new-feature
```
* Go to GitHub.com
* Click **Compare & pull request**
* Review your changes visually to catch typos
* Click **Merge pull request** to merge your code into `main`

### Step 5: Deploy to Production VM
Now that `main` is officially updated, SSH into your server and deploy the tested code.
```bash
ssh azureuser@<your-vm-ip>
cd ~/gmail-triage
git pull origin main
docker compose up -d --build
```
```

---

## 3. Git Commands Cheat Sheet

Here is a quick reference guide from basic everyday commands to advanced recovery commands.

### The Basics (Everyday Usage)
* `git status` - Tells you what branch you're on and what files are modified.
* `git add .` - Stages **all** modified files to be committed.
* `git add src/file.py` - Stages only a **specific** file to be committed.
* `git commit -m "your message"` - Saves your staged changes locally with a descriptive message.
* `git push` - Uploads your committed changes to GitHub.
* `git pull` - Downloads the latest changes from GitHub to your laptop.

### Branching & Navigation
* `git branch` - Lists all your local branches.
* `git switch <branch-name>` - Moves you to an existing branch.
* `git switch -c <new-branch-name>` - Creates a new branch and immediately switches to it.
* `git switch main` - Returns you to your main code.

### Advanced (Undo & Fix Mistakes)
* `git log` - Shows the history of all commits. Press `q` to exit.
* `git restore src/file.py` - **DANGER:** Undoes all unsaved changes in a file, reverting it to the last commit.
* `git reset HEAD~1` - **DANGER:** Undoes your very last commit, but keeps the file modifications so you can edit and try committing again. 
* `git stash` - Temporarily hides your uncommitted changes so you can switch branches.
* `git stash pop` - Brings your hidden changes back.

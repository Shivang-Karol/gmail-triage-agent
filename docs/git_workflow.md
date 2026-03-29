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

# ☁️ Azure VM Deployment Guide

This guide walks you through deploying the Gmail Triage Agent to a cloud server so it runs 24/7 — even when your computer is off.

**No prior cloud or Docker experience is required.** Every step is copy-paste.

---

## What You'll Need Before Starting

Before touching Azure, make sure you've completed these on your **local PC** first:

1. ✅ Cloned this repository
2. ✅ Filled in your `.env` file (copy from `.env.example`)
3. ✅ Placed your `credentials.json` in the project root
4. ✅ Run `py -3.12 main.py run` at least once locally (this generates `token.json` via a browser popup — you **cannot** do this on a headless cloud server)

> [!IMPORTANT]
> The `token.json` file is your Gmail access pass. It can only be created on a computer with a web browser. You must generate it locally first, then transfer it to the cloud.

---

## Step 1: Create Your Azure VM

1. Go to [portal.azure.com](https://portal.azure.com) and sign in.
2. Click **"Create a resource"** → **"Virtual Machine"**.
3. Fill in the settings:

| Setting | Recommended Value |
| :--- | :--- |
| **Resource Group** | `gmail-triage-group` (create new) |
| **VM Name** | `gmail-triage-vm` |
| **Region** | Pick one where `B2ats_v2` shows as "Free services eligible" (try East US) |
| **Image** | `Ubuntu Server 24.04 LTS - x64 Gen2` |
| **Size** | e.g. `Standard_B2ats_v2` (2 vCPUs, 1 GB RAM) — look for whichever instance currently has the **"free services eligible"** tag |
| **Authentication** | SSH public key (Azure will generate one for you) |
| **Username** | `azureuser` |
| **Inbound Ports** | Allow **SSH (22)** only |

4. Go to the **Disks** tab → change "OS disk type" to **Standard SSD** (saves money).
5. Click **Review + create** → **Create**.
6. **Download the `.pem` key file** when prompted. Save it somewhere safe — you cannot download it again!

> [!TIP]
> At the time of writing, free-tier eligible SKUs (like `B2ats_v2`) are free for 750 hours/month (that's more than a full month of 24/7 running). Please check current Azure pricing pages to confirm eligibility.

---

## Step 2: Log Into Your VM

Open **Windows Terminal** or **PowerShell** and run:

```powershell
ssh -i "C:\path\to\your-key.pem" azureuser@<your-vm-public-ip>
```

**First time?** Type `yes` when asked about the host fingerprint.

**Getting a "permissions too open" error?** Fix it with:
```powershell
icacls "C:\path\to\your-key.pem" /inheritance:r
icacls "C:\path\to\your-key.pem" /grant:r "%USERNAME%:R"
```
Then try the SSH command again.

---

## Step 3: Install Docker on the VM

Once you're logged in (you'll see `azureuser@gmail-triage-vm:~$`), paste this entire block:

```bash
sudo apt-get update && sudo apt-get upgrade -y && \
curl -fsSL https://get.docker.com -o get-docker.sh && \
sudo sh get-docker.sh && \
sudo apt-get install -y docker-compose-plugin && \
sudo usermod -aG docker $USER && \
mkdir -p ~/gmail-triage && \
echo "✅ Docker installed! Type 'exit' and log back in to continue."
```

After it finishes, type `exit` and SSH back in. This activates the Docker permissions.

---

## Step 4: Transfer Your Code and Secrets

Run these from your **local Windows terminal** (not the VM):

### Transfer application code:
```powershell
scp -i "C:\path\to\your-key.pem" Dockerfile docker-compose.yml main.py schema.sql requirements.txt .dockerignore azureuser@<your-ip>:~/gmail-triage/

scp -i "C:\path\to\your-key.pem" -r src config scripts azureuser@<your-ip>:~/gmail-triage/
```

### Transfer secrets (the important part!):
```powershell
scp -i "C:\path\to\your-key.pem" .env token.json credentials.json azureuser@<your-ip>:~/gmail-triage/
```

> [!WARNING]
> These secret files (`.env`, `token.json`, `credentials.json`) give full access to your Gmail and AI accounts. Transfer them over SSH only — never put them in a public place.

---

## Step 5: Start the Bot

SSH back into your VM and run:

```bash
cd ~/gmail-triage
docker compose up -d --build
```

The first build takes 2-3 minutes. After that, your bot is running!

---

## Step 6: Verify It's Working

Check the logs:
```bash
docker compose logs --tail=30
```

You should see output like:
```
gmail-triage-agent | Gmail Triage Agent — Starting Run
gmail-triage-agent | [Phase 1/2] Running Ingestor...
gmail-triage-agent | Ingestion complete. Queued: 5, Skipped (Privacy): 0
gmail-triage-agent | [Phase 2/2] Running Worker...
gmail-triage-agent | Sleeping for 60 minutes until next run...
```

**That's it! Your bot is now running 24/7 in the cloud.** 🎉

---

## Daily Operations Cheat Sheet

All of these commands are run **on the VM** (SSH in first):

| What you want to do | Command |
| :--- | :--- |
| Watch live logs | `docker compose logs -f --tail=20` |
| Stop the bot | `docker compose down` |
| Restart the bot | `docker compose up -d` |
| Rebuild after code changes | `docker compose up -d --build` |
| Run one triage cycle manually | `docker exec gmail-triage-agent python main.py run` |
| Check queue health | `docker exec gmail-triage-agent python main.py status` |
| Run a database backup | `docker exec gmail-triage-agent python main.py backup` |

---

## Updating the Bot

When you make code changes locally:

1. Push changes to GitHub from your PC
2. SSH into your VM
3. Pull and rebuild:
```bash
cd ~/gmail-triage
# Transfer updated files via scp (same commands as Step 4)
docker compose up -d --build
```

---

## Cost Breakdown

*Note: Cloud pricing changes frequently. This is an approximate example based on 2024/2025 Azure pricing.*

| Resource | Estimated Cost |
| :--- | :--- |
| VM (Free Tier Eligible) | **Free** for 12 months (750 hrs/month), then ~$5/month |
| OS Disk (Standard SSD, 30GB) | ~$2/month (often included in free tier) |
| Public IP | ~$3/month |
| **Total (Year 1)** | **~$3-5/month** |
| **Total (After Year 1)** | **~$10/month** |

> [!TIP]
> With $100 in student or startup cloud credits, this setup will last comfortably for **over 2 years** of continuous operation.

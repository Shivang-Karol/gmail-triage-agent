# Azure VM Deployment Guide for Gmail Triage Agent

This guide covers setting up an Azure Virtual Machine and deploying the containerized `gmail-triage` agent.

## 1. Provisioning the VM (Azure Portal)

1.  **Create a Resource Group**: Name it something like `gmail-triage-group`.
2.  **Create a Virtual Machine**:
    *   **Image**: Ubuntu 22.04 LTS (or similar Linux).
    *   **Size**: `Standard_B1s` (1 vCPU, 1 GB RAM) is sufficient.
    *   **Authentication type**: SSH public key (recommended).
    *   **Public IP**: Ensure "Standard" Public IP is created.
    *   **NSG (Network Security Group)**: Allow inbound `SSH` (port 22) from your IP.
3.  **Note the Public IP address** once created.

---

## 2. Server Configuration

Connect to your VM via SSH:
```bash
ssh <admin-user>@<your-vps-ip>
```

### Install Docker & Docker Compose
Run these commands to get your Linux environment ready:
```bash
# Update packages
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get install -y docker-compose-plugin

# Add your user to the docker group
sudo usermod -aG docker $USER
```
*(Logout and log back in for the group changes to take effect)*

---

## 3. Deployment Steps

### Prepare the Application Directory
```bash
mkdir ~/gmail-triage
cd ~/gmail-triage
```

### Transfer Files
From your **local computer**, transfer the following files (using `scp` or a similar tool):
```powershell
# Copy core files (Run from YOUR computer, not the VM)
scp Dockerfile docker-compose.yml main.py schema.sql <admin-user>@<vps-ip>:~/gmail-triage/
scp -r src/ <admin-user>@<vps-ip>:~/gmail-triage/
scp -r config/ <admin-user>@<vps-ip>:~/gmail-triage/
scp -r scripts/ <admin-user>@<vps-ip>:~/gmail-triage/
```

### Inject Secrets (CRITICAL)
Transfer your current secrets (highly sensitive):
```powershell
scp .env token.json credentials.json <admin-user>@<vps-ip>:~/gmail-triage/
```

---

## 4. Launching the Agent

On the **VM**, run:
```bash
cd ~/gmail-triage
docker-compose up -d --build
```

Monitor logs:
```bash
docker-compose logs -f
```

The agent is now running as a background daemon and will check your Gmail every hour automatically!

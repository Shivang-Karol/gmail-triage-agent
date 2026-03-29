# Cloud Deployment Secrets & Security Workflow

When transitioning Gmail Triage to a 24/7 autonomous cloud-hosted Docker container, security and credential management are completely different from running it locally on a Windows PC.

Here is the rigid workflow to follow to supply credentials without baking them into the container image or publicly exposing them.

## 1. Environment Variables Injection

Your application relies on sensitive keys (like `GEMINI_API_KEY`) and dynamic config variables defined in your `.env` file. These are intentionally excluded by `.dockerignore`.

On your **Azure VM**, the `.env` file is transferred directly via `scp` and mounted into the container at runtime as a read-only bind mount. Your `docker-compose.yml` handles this automatically:

```yaml
volumes:
  - ./.env:/app/.env:ro
```

This means the `.env` file is never baked into the Docker image layer, but is available to the running container.

## 2. OAuth Cloud Bridging Workflow

The Gmail API requires `token.json` for persistent OAuth access. Generating this file requires a browser popup which is **impossible** on a headless cloud server.

### The Correct Workflow:
1. **Generate Token Locally**: Run the application locally on your Windows machine at least once. This will open your web browser. Grant access. This generates the `token.json` on your PC.
2. **Transfer to Cloud**: Use `scp` to copy the token directly to your VM:
   ```powershell
   scp -i "<path/to/your/key.pem>" token.json credentials.json azureuser@<your-ip>:~/gmail-triage/
   ```
3. **Persistence**: The `docker-compose.yml` mounts `token.json` as a read-only bind mount, so it survives container restarts.

> [!WARNING]
> Never commit `token.json` or `credentials.json` to Git. The `.gitignore` already protects these. Doing so will bake permanent administrative access to your Gmail account into the repo.

## 3. Automated Database Backups

A cloud-friendly shell script `scripts/backup.sh` replaces the Windows-centric `backup.ps1`.
- It uses `gzip` to compress the `app_data.db`.
- It retains only the 7 most recent backup files to prevent disk bloat.
- On Azure, trigger it manually with:
  ```bash
  docker exec gmail-triage-agent python main.py backup
  ```


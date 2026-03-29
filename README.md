# 📧 Gmail Triage Agent - Master Manual

Your personal, AI-powered executive assistant that lives inside your Gmail. It works silently in the background to organize your inbox so you can focus on what matters.

---

## 🚀 The Dashboard (manage_agent.bat)

The easiest way to control your agent is by using the **`manage_agent.bat`** file in the project folder.

- **Option 1: EXAM MODE** 🎓 
  - Instantly turns off all background tasks and stops any running processes. Use this when you need 100% focus and zero background noise.
- **Option 2: NORMAL MODE** ✅ 
  - Resumes the background triage. The agent will check your mail every **10 minutes** (5 emails per batch).
- **Option 3: STATUS Check** 📊 
  - Shows you exactly if the tasks are "Ready" or "Disabled."

---

## 🛠️ Manual Controls (For Power Users)

If you're in the terminal (`d:\New folder\gmail-triage`), you can run these commands for deeper insights:

| Task | Command |
| :--- | :--- |
| **Check Health** | `py -3.12 main.py status` |
| **Weekly Report** | `py -3.12 main.py digest` |
| **Manual Backup** | `py -3.12 main.py backup` |
| **Retry Failed Mail** | `py -3.12 main.py replay` |

---

## ⚙️ Configuration (agent_config.yaml)

You can customize how the agent thinks by editing this file:
- **Add Categories**: Want a `SCHOLARSHIP` label? Add it to the `categories` list.
- **Exclude Senders**: Add domains like `amazon.com` or your bank to `exclude_sender_domains` to make the AI ignore them completely.
- **Daily Cap**: The agent is limited to **300 calls/day** to keep it free. You can change this in `daily_call_cap`.

---

## 🚨 Maintenance & Troubleshooting

### 1. "API Key Not Valid"
If your Gemini API Key changes or expires, update the `.env` file:
```text
GEMINI_API_KEY=your_new_key_here
```

### 2. "Gmail Token Expired"
If you see an error about Gmail permissions, simply delete the **`token.json`** file and run `py -3.12 main.py`. A browser window will open for you to log in and grant access again.

### 3. Missing Emails?
- **Is it too new?** The agent checks every 10 minutes.
- **Is it confidential?** Check `exclude_sender_domains` to see if it's being filtered.
- **Is it low confidence?** Look at your Gmail for a `REVIEW_NEEDED` label—it might be there!

---

## 🔒 Security & Privacy
- **PII Redacted**: Phone numbers, SSNs, and Student IDs are removed **locally** before your email ever reaches Gemini.
- **Offline Reliability**: If your internet is out, the agent waits and tries again later. If Gemini is down, it uses a local "Keyword Fallback" to ensure your mail is still organized.

---

### Developed with Antigravity 🚀
Enjoy your newly organized inbox!

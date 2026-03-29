# Note 001: Keeping the AI Calm (Rate Limits)

### 💡 The Problem
When you first start this bot, you might have hundreds of unread emails. If the bot tries to send all of them to the Google AI (Gemini) at the same time, the AI gets overwhelmed and starts returning "Too Many Requests" errors. This is because the free version of Gemini only allows a few emails per minute.

### ✅ The Solution: "Polite Mode"
We taught the bot to be patient! Instead of rushing through your inbox, it now waits for **12 seconds** after processing each email. 

By taking this small break, the bot stays within Google's "speed limit." It’s a bit slower at the very beginning (processing about 5 emails per minute), but it ensures that **every single email** gets filed correctly without crashing.

### 📈 Result
No more "Busy" errors. The bot can now work through your entire backlog steadily and reliably without you needing to do anything.

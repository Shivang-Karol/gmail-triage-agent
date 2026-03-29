# Incident 001: Gemini Free Tier Rate Limits

## The Problem
When the initial ingestion caught a 100+ email backlog, the Google Gemini API ("gemini-2.5-flash") immediately returned a `429 Too Many Requests` error, stalling the triage loop.
The Free Tier limit is strictly **5 RPM (Requests Per Minute)**. The agent was bursting batches of 20 emails simultaneously.

## The Solution: "Polite Mode"
Instead of complex exponential backoff queues, we introduced a deterministic internal jitter at the worker level. 

```python
if used_model != "fallback_rules":
    logger.info("Polite Mode: Sleeping 12s to respect Free Tier rate limits...")
    time.sleep(12)
```

By enforcing a hard 12-second sleep *after* any successful `used_model` invocation, we artificially cap the burst rate to exactly 5 requests per 60 seconds (5 * 12s = 60s). This perfectly skirts the 5 RPM constraint without abandoning real-time queueing.

## Result
Zero 429 errors since implementation. Queue processes steadily at ~300 emails per hour (the hard daily cap limit).

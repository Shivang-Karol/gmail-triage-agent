# Incident 002: Reconciliation Checkpoint & "Missing" Read Emails

## The Problem
The original ingestor loop only searched for `is:unread`. 
If a user manually checked their inbox from their phone and opened a high-priority "Placement" email *before* the 10-minute triage cycle fired, that email would lose its "unread" status and permanently bypass our AI classification.

## The Solution: The "Dual-Query" Strategy
We introduced an idempotent SQLite tracking tier to store a `last_ingest_timestamp` checkpoint.

The ingestor now runs two consecutive queries over the Gmail API:
1. `is:unread` (Catches active influx)
2. `after:{last_checkpoint}` (Catches all newly arrived mail, regardless of human interaction)

Since the `db.upsert_email()` function ignores duplicate insertions, we safely ingest the union of these two queries. 

## Result
Zero dropped emails. The agent acts securely as an asynchronous background worker, providing eventual consistency even if the user races the worker to read the email first.

import logging
import json
from datetime import datetime, timedelta, timezone
from src.db import get_connection

logger = logging.getLogger(__name__)

def generate_weekly_report():
    """
    Queries the database for all completed categorizations in the last 7 days.
    Returns a formatted string summary.
    """
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT classification_json, created_at 
            FROM emails 
            WHERE status = 'completed' AND created_at >= ?
        """, (seven_days_ago,))
        rows = cursor.fetchall()
        
    if not rows:
        return "No emails processed in the last 7 days."
        
    stats = {}
    urgent_items = []
    
    for row in rows:
        data = json.loads(row['classification_json'])
        cat = data.get('category', 'OTHER')
        stats[cat] = stats.get(cat, 0) + 1
        
        # Track items that would have triggered a notification
        if cat in ["INTERVIEW_SCHEDULE", "DEADLINE_ALERT", "PLACEMENT"]:
            urgent_items.append({
                "category": cat,
                "summary": data.get('summary', 'No summary'),
                "date": row['created_at']
            })
            
    report = []
    report.append("="*40)
    report.append(" GMAIL TRIAGE AGENT - WEEKLY DIGEST")
    report.append("="*40)
    report.append(f"Period: {seven_days_ago.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
    report.append(f"Total Emails Processed: {len(rows)}")
    report.append("-" * 20)
    report.append("Status Breakdown:")
    for cat, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        report.append(f"  {cat:20s}: {count:d}")
        
    if urgent_items:
        report.append("-" * 20)
        report.append("Urgent Highlights:")
        for item in urgent_items[:10]: # Top 10
            report.append(f"  [{item['category']}] {item['summary']} ({item['date']})")
            
    report.append("=" * 40)
    return "\n".join(report)

if __name__ == "__main__":
    print(generate_weekly_report())

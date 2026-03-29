"""
Windows Desktop Notifications for high-urgency emails.
Uses PowerShell toast notifications (no extra dependencies needed).
"""
import subprocess
import logging

logger = logging.getLogger(__name__)

def send_toast_notification(title: str, message: str):
    """
    Sends a Windows 10/11 toast notification using PowerShell.
    No external libraries required.
    """
    # Escape single quotes for PowerShell
    title = title.replace("'", "''")
    message = message.replace("'", "''")
    
    ps_script = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

    $template = @'
    <toast>
        <visual>
            <binding template="ToastGeneric">
                <text>{title}</text>
                <text>{message}</text>
            </binding>
        </visual>
        <audio src="ms-winsoundevent:Notification.Mail"/>
    </toast>
'@

    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Gmail Triage Agent').Show($toast)
    """
    
    try:
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True, timeout=10
        )
        logger.info(f"Desktop notification sent: {title}")
    except Exception as e:
        logger.warning(f"Failed to send desktop notification: {e}")


def notify_if_urgent(classification: dict, email_summary: str = ""):
    """
    Check if the classification warrants an urgent desktop alert.
    Called by the worker after a successful classification.
    """
    urgent_categories = {"INTERVIEW_SCHEDULE", "DEADLINE_ALERT", "PLACEMENT"}
    
    category = classification.get("category", "")
    confidence = classification.get("confidence", 0)
    summary = classification.get("summary", email_summary)
    
    if category in urgent_categories and confidence >= 0.80:
        send_toast_notification(
            title=f"🚨 {category.replace('_', ' ').title()}",
            message=summary
        )

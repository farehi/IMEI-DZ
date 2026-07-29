import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(to: str, subject: str, body: str) -> bool:
    """Send email if SMTP is configured. Returns True on success."""
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", user)

    if not all([host, user, password, to]):
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception:
        return False


def notify_admin_telegram(text: str) -> bool:
    """Send Telegram message to admin if bot token + chat id set."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    try:
        import urllib.request
        import urllib.parse
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


def notify_report_status(owner_contact: str, reference: str, status: str) -> None:
    """Notify owner when report is approved/rejected (email if contact looks like email)."""
    if "@" not in (owner_contact or ""):
        return
    status_ar = {"approved": "مقبول", "rejected": "مرفوض"}.get(status, status)
    subject = f"تحديث بلاغ {reference} — {status_ar}"
    body = f"مرحباً،\n\nتم تحديث حالة بلاغك رقم {reference} إلى: {status_ar}.\n\nمدقق الهواتف المسروقة"
    send_email(owner_contact, subject, body)

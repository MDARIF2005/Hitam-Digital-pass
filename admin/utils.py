from datetime import datetime
import os
import smtplib
from email.message import EmailMessage


def send_password_reset_email(to_email, new_password, name=None):
    """Send a simple password reset email using SMTP settings from env vars.

    Required environment variables:
    - SMTP_HOST
    - SMTP_PORT
    - SMTP_USER
    - SMTP_PASSWORD
    - SMTP_FROM
    Returns True if sent, False otherwise.
    """
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = os.getenv('SMTP_PORT')
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_from = os.getenv('SMTP_FROM')

    if not all([smtp_host, smtp_port, smtp_user, smtp_password, smtp_from]):
        return False

    subject = 'Your account password has been reset'
    display_name = name or ''
    body = f"Hello {display_name},\n\nYour account password has been reset.\n\nNew password: {new_password}\n\nPlease change your password after logging in.\n\nRegards,\nAdmin"

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = smtp_from
        msg['To'] = to_email
        msg.set_content(body)

        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        return False

def format_datetime(value, format='%Y-%m-%d %H:%M'):
    """Format a datetime object for display."""
    if isinstance(value, datetime):
        return value.strftime(format)
    return value

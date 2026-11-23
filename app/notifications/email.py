import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_test_email(recipient: str | None = None) -> None:
    recipient = recipient or settings.notify_email
    if not recipient or not settings.smtp_host:
        raise ValueError("Configure SMTP_HOST and NOTIFY_EMAIL first.")
    message = EmailMessage()
    message["Subject"] = "Job Search Assistant Test"
    message["From"] = settings.email_from or settings.smtp_username
    message["To"] = recipient
    message.set_content("The Job Search Assistant email configuration is working.")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)

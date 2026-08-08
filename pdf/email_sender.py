"""Automated Email Sender Module.

Dispatches individual emails with attached customized PDFs via SMTP.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Dict, Any, Optional


def send_email_with_pdf_attachment(
    to_email: str,
    subject: str,
    body_text: str,
    attachment_pdf_path: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    sender_email: str = "",
    sender_password: str = ""
) -> Dict[str, Any]:
    """Sends an individual automated email with attached PDF to recipient."""
    if not sender_email:
        sender_email = os.environ.get("SMTP_SENDER_EMAIL", "")
    if not sender_password:
        sender_password = os.environ.get("SMTP_SENDER_PASSWORD", "")
    if not smtp_host:
        smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")

    if not sender_email or not sender_password:
        return {
            "success": False,
            "error": "Missing SMTP sender credentials. Please configure sender email and password.",
            "recipient": to_email
        }

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body_text, "plain"))

        # Attach PDF
        if os.path.exists(attachment_pdf_path):
            filename = os.path.basename(attachment_pdf_path)
            with open(attachment_pdf_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=filename)
                part['Content-Disposition'] = f'attachment; filename="{filename}"'
                msg.attach(part)

        if int(smtp_port) == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()

        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        return {"success": True, "recipient": to_email}
    except Exception as e:
        return {"success": False, "error": str(e), "recipient": to_email}

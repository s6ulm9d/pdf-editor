"""Automated Email Sender Module.

Dispatches individual emails with attached customized PDFs via SMTP.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Dict, Any, Optional


def test_smtp_connection(
    smtp_host: str = "smtp.hostinger.com",
    smtp_port: int = 465,
    sender_email: str = "",
    sender_password: str = ""
) -> Dict[str, Any]:
    """Tests connection and authentication to the SMTP server."""
    if not sender_email:
        sender_email = os.environ.get("SMTP_SENDER_EMAIL", "")
    if not sender_password:
        sender_password = os.environ.get("SMTP_SENDER_PASSWORD", "")
    if not smtp_host:
        smtp_host = os.environ.get("SMTP_HOST", "smtp.hostinger.com")

    if not sender_email or not sender_password:
        return {
            "success": False,
            "error": "Missing credentials. Please enter Sender Email and Password."
        }

    try:
        if int(smtp_port) == 465:
            server = smtplib.SMTP_SSL(smtp_host, int(smtp_port), timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, int(smtp_port), timeout=15)
            server.starttls()

        server.login(sender_email, sender_password)
        server.quit()
        return {
            "success": True,
            "message": f"Successfully connected & authenticated to {smtp_host}:{smtp_port} as {sender_email}!"
        }
    except Exception as e:
        err_msg = str(e)
        if "535" in err_msg or "authentication failed" in err_msg.lower():
            err_msg = f"Authentication Failed (535): Incorrect password or username for {sender_email}. Please check your email password."
        return {
            "success": False,
            "error": err_msg
        }


def send_email_with_pdf_attachment(
    to_email: str,
    subject: str,
    body_text: str,
    attachment_pdf_path: str,
    smtp_host: str = "smtp.hostinger.com",
    smtp_port: int = 465,
    sender_email: str = "",
    sender_password: str = ""
) -> Dict[str, Any]:
    """Sends an individual automated email with attached PDF to recipient."""
    if not sender_email:
        sender_email = os.environ.get("SMTP_SENDER_EMAIL", "")
    if not sender_password:
        sender_password = os.environ.get("SMTP_SENDER_PASSWORD", "")
    if not smtp_host:
        smtp_host = os.environ.get("SMTP_HOST", "smtp.hostinger.com")

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
            server = smtplib.SMTP_SSL(smtp_host, int(smtp_port), timeout=25)
        else:
            server = smtplib.SMTP(smtp_host, int(smtp_port), timeout=25)
            server.starttls()

        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        return {"success": True, "recipient": to_email}
    except Exception as e:
        err_str = str(e)
        if "535" in err_str or "authentication failed" in err_str.lower():
            err_str = "Authentication Failed (535): Password rejected by SMTP server."
        return {"success": False, "error": err_str, "recipient": to_email}

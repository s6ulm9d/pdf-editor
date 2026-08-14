"""Automated Email Sender Module.

Dispatches individual emails with attached customized PDFs via SMTP.
Applies clean IPv4 DNS resolution to prevent '[Errno 101] Network is unreachable' on cloud hosts.
"""

import os
import socket
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Dict, Any, Optional

# Force socket getaddrinfo to prioritize AF_INET (IPv4) to prevent Errno 101 on cloud platforms
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if family == 0 or family == socket.AF_UNSPEC:
        family = socket.AF_INET
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _ipv4_getaddrinfo


def _get_smtp_server(smtp_host: str, smtp_port: int, timeout: int = 20) -> smtplib.SMTP:
    """Returns an authenticated SMTP / SMTP_SSL server instance."""
    port_num = int(smtp_port)
    if port_num == 465:
        return smtplib.SMTP_SSL(smtp_host, port_num, timeout=timeout)
    else:
        server = smtplib.SMTP(smtp_host, port_num, timeout=timeout)
        server.starttls()
        return server


def test_smtp_connection(
    smtp_host: str = "smtp.hostinger.com",
    smtp_port: int = 465,
    sender_email: str = "",
    sender_password: str = ""
) -> Dict[str, Any]:
    """Tests connection and authentication to the SMTP server with clean IPv4 resolution."""
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

    # Try requested port first, fallback to alternative port if network fails
    ports_to_try = [int(smtp_port)]
    alt_port = 587 if int(smtp_port) == 465 else 465
    ports_to_try.append(alt_port)

    last_error = ""
    for port in ports_to_try:
        try:
            server = _get_smtp_server(smtp_host, port, timeout=15)
            server.login(sender_email, sender_password)
            server.quit()
            return {
                "success": True,
                "message": f"Successfully connected & authenticated to {smtp_host}:{port} as {sender_email}!"
            }
        except Exception as e:
            err_msg = str(e)
            if "535" in err_msg or "authentication failed" in err_msg.lower():
                return {
                    "success": False,
                    "error": f"Authentication Failed (535): Incorrect password or username for {sender_email}. Please check your email password."
                }
            last_error = err_msg

    return {
        "success": False,
        "error": f"SMTP Connection Failed ({smtp_host}): {last_error}"
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
    """Sends an individual automated email with attached PDF to recipient using native IPv4 resolution."""
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

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))

    # Attach PDF if it exists
    if os.path.exists(attachment_pdf_path):
        filename = os.path.basename(attachment_pdf_path)
        with open(attachment_pdf_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=filename)
            part['Content-Disposition'] = f'attachment; filename="{filename}"'
            msg.attach(part)

    ports_to_try = [int(smtp_port)]
    alt_port = 587 if int(smtp_port) == 465 else 465
    ports_to_try.append(alt_port)

    last_err = ""
    for port in ports_to_try:
        try:
            server = _get_smtp_server(smtp_host, port, timeout=25)
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            return {"success": True, "recipient": to_email}
        except Exception as e:
            err_str = str(e)
            if "535" in err_str or "authentication failed" in err_str.lower():
                return {
                    "success": False,
                    "error": "Authentication Failed (535): Password rejected by SMTP server.",
                    "recipient": to_email
                }
            last_err = err_str

    return {
        "success": False,
        "error": f"SMTP Dispatch Error ({smtp_host}): {last_err}",
        "recipient": to_email
    }

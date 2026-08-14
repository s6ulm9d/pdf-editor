"""Automated Email Sender Module.

Dispatches individual emails with attached customized PDFs via SMTP or HTTP Email API (Resend / Brevo).
Prevents '[Errno 101] Network is unreachable' on cloud hosts (e.g. Railway) where raw SMTP ports are blocked.
"""

import os
import socket
import smtplib
import ssl
import json
import base64
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Dict, Any, Optional

# Prioritize AF_INET (IPv4) resolution
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if family == 0 or family == socket.AF_UNSPEC:
        family = socket.AF_INET
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _ipv4_getaddrinfo


def _send_via_resend_api(api_key: str, from_email: str, to_email: str, subject: str, body_text: str, pdf_path: str) -> Dict[str, Any]:
    """Dispatches email using Resend HTTP API (Port 443 HTTPS - Never blocked by cloud firewalls)."""
    try:
        attachments = []
        if pdf_path and os.path.exists(pdf_path):
            filename = os.path.basename(pdf_path)
            with open(pdf_path, "rb") as f:
                b64_content = base64.b64encode(f.read()).decode("utf-8")
            attachments.append({
                "filename": filename,
                "content": b64_content
            })

        payload = {
            "from": from_email or "onboarding@resend.dev",
            "to": [to_email],
            "subject": subject,
            "text": body_text,
            "attachments": attachments
        }

        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "recipient": to_email, "id": data.get("id")}
    except Exception as e:
        return {"success": False, "error": f"Resend API Error: {str(e)}", "recipient": to_email}


def _send_via_brevo_api(api_key: str, from_email: str, to_email: str, subject: str, body_text: str, pdf_path: str) -> Dict[str, Any]:
    """Dispatches email using Brevo (Sendinblue) HTTP API (Port 443 HTTPS)."""
    try:
        attachments = []
        if pdf_path and os.path.exists(pdf_path):
            filename = os.path.basename(pdf_path)
            with open(pdf_path, "rb") as f:
                b64_content = base64.b64encode(f.read()).decode("utf-8")
            attachments.append({
                "name": filename,
                "content": b64_content
            })

        payload = {
            "sender": {"email": from_email or "hr@support.algoryx.in", "name": "HR Team"},
            "to": [{"email": to_email}],
            "subject": subject,
            "textContent": body_text,
            "attachment": attachments
        }

        req = urllib.request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "api-key": api_key,
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "recipient": to_email, "id": data.get("messageId")}
    except Exception as e:
        return {"success": False, "error": f"Brevo API Error: {str(e)}", "recipient": to_email}


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
    """Tests connection and authentication to the SMTP server or HTTP Mail API."""
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

    # Resend API Key check
    if sender_password.startswith("re_"):
        res = _send_via_resend_api(sender_password, sender_email, sender_email, "SMTP Test", "Test", "")
        if res.get("success"):
            return {"success": True, "message": f"Successfully authenticated via Resend HTTP API (Port 443) as {sender_email}!"}
        else:
            return {"success": False, "error": res.get("error")}

    # Brevo API Key check
    if sender_password.startswith("xkeysib-"):
        res = _send_via_brevo_api(sender_password, sender_email, sender_email, "SMTP Test", "Test", "")
        if res.get("success"):
            return {"success": True, "message": f"Successfully authenticated via Brevo HTTP API (Port 443) as {sender_email}!"}
        else:
            return {"success": False, "error": res.get("error")}

    # Standard SMTP
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
            if "101" in err_msg or "unreachable" in err_msg.lower() or "111" in err_msg or "refused" in err_msg.lower():
                last_error = f"Railway cloud firewall blocks outbound raw TCP ports 465/587. Use a Resend API Key (re_...) or Brevo API Key (xkeysib-...) for 100% HTTPS email dispatch over Port 443."
            else:
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
    """Sends an individual automated email with attached PDF to recipient using SMTP or HTTP Mail API."""
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

    # HTTP API dispatch if API key supplied
    if sender_password.startswith("re_"):
        return _send_via_resend_api(sender_password, sender_email, to_email, subject, body_text, attachment_pdf_path)

    if sender_password.startswith("xkeysib-"):
        return _send_via_brevo_api(sender_password, sender_email, to_email, subject, body_text, attachment_pdf_path)

    # Standard SMTP dispatch
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))

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
            if "101" in err_str or "unreachable" in err_str.lower():
                last_err = "Railway cloud firewall blocks outbound raw TCP ports 465/587. Use Resend/Brevo HTTP API Key for Port 443 dispatch."
            else:
                last_err = err_str

    return {
        "success": False,
        "error": f"SMTP Dispatch Error ({smtp_host}): {last_err}",
        "recipient": to_email
    }

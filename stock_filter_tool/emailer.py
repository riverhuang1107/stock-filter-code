from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_RECIPIENTS = [
    "riverhuang82@gmail.com",
    "ceciliawangxi@gmail.com",
    "ceciliawangxi@126.com",
]


def send_report_email(
    html: str,
    recipients: list[str] | None = None,
    subject: str = "A股大阳包小阴筛选报告",
    attachments: list[Path] | None = None,
) -> None:
    load_dotenv()
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("MAIL_FROM") or user
    missing = [name for name, value in {
        "SMTP_HOST": host,
        "SMTP_USER": user,
        "SMTP_PASSWORD": password,
        "MAIL_FROM/SMTP_USER": sender,
    }.items() if not value]
    if missing:
        raise RuntimeError(f"Missing SMTP configuration: {', '.join(missing)}")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients or DEFAULT_RECIPIENTS)
    msg.set_content("请使用支持 HTML 的邮件客户端查看 A股大阳包小阴筛选报告。")
    msg.add_alternative(html, subtype="html")
    for path in attachments or []:
        msg.add_attachment(path.read_bytes(), maintype="application", subtype="octet-stream", filename=path.name)
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)

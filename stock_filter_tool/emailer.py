from __future__ import annotations

import base64
import json
import os
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


DEFAULT_RECIPIENTS = [
    "riverhuang82@gmail.com",
    "ceciliawangxi@gmail.com",
    "ceciliawangxi@126.com",
]

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
DEFAULT_CREDENTIALS_FILE = Path("secrets/gmail_credentials.json")
DEFAULT_TOKEN_FILE = Path("secrets/gmail_token.json")


def send_report_email(
    html: str,
    recipients: list[str] | None = None,
    subject: str = "A股大阳包小阴筛选报告",
    attachments: list[Path] | None = None,
) -> None:
    load_dotenv()
    service = _build_gmail_service()
    msg = build_report_message(
        html=html,
        recipients=recipients or DEFAULT_RECIPIENTS,
        subject=subject,
        attachments=attachments or [],
    )
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def authorize_gmail(force: bool = False, console: bool = False) -> Path:
    load_dotenv()
    token_path = _token_path()
    if token_path.exists() and not force:
        return token_path

    flow = _load_installed_app_flow()
    if console:
        creds = _run_console_flow(flow)
    else:
        creds = flow.run_local_server(port=8080, host="localhost", open_browser=True)

    _save_token(creds, token_path)
    return token_path


def build_report_message(
    html: str,
    recipients: list[str],
    subject: str = "A股大阳包小阴筛选报告",
    attachments: list[Path] | None = None,
) -> EmailMessage:
    sender = os.getenv("MAIL_FROM") or "me"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content("请使用支持 HTML 的邮件客户端查看 A股大阳包小阴筛选报告。")
    msg.add_alternative(html, subtype="html")
    for path in attachments or []:
        msg.add_attachment(path.read_bytes(), maintype="application", subtype="octet-stream", filename=path.name)
    return msg


def _build_gmail_service():
    from googleapiclient.discovery import build

    creds = _load_credentials()
    return build("gmail", "v1", credentials=creds)


def _load_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    token_info = _load_token_info()
    creds = Credentials.from_authorized_user_info(token_info, scopes=[GMAIL_SEND_SCOPE]) if token_info else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds, _token_path())
    if not creds or not creds.valid:
        raise RuntimeError(
            "Gmail OAuth token is missing or invalid. Run: "
            "python -m stock_filter_tool gmail-auth"
        )
    return creds


def _load_installed_app_flow():
    from google_auth_oauthlib.flow import InstalledAppFlow

    credentials_info = _load_credentials_info()
    return InstalledAppFlow.from_client_config(credentials_info, scopes=[GMAIL_SEND_SCOPE])


def _run_console_flow(flow: Any):
    flow.redirect_uri = "http://localhost"
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    print("Open this URL in a browser and authorize Gmail sending:")
    print(auth_url)
    print("After approval, copy the full redirected URL from the browser address bar.")
    redirected_url = input("Paste the full redirected URL here: ").strip()
    flow.fetch_token(authorization_response=redirected_url)
    return flow.credentials


def _load_credentials_info() -> dict[str, Any]:
    raw = os.getenv("GMAIL_CREDENTIALS_JSON")
    if raw:
        return json.loads(raw)
    credentials_path = _credentials_path()
    if not credentials_path.exists():
        raise RuntimeError(
            f"Missing Gmail OAuth client file: {credentials_path}. "
            "Download an OAuth desktop client JSON from Google Cloud Console."
        )
    return json.loads(credentials_path.read_text(encoding="utf-8"))


def _load_token_info() -> dict[str, Any] | None:
    raw = os.getenv("GMAIL_TOKEN_JSON")
    if raw:
        return json.loads(raw)
    token_path = _token_path()
    if not token_path.exists():
        return None
    return json.loads(token_path.read_text(encoding="utf-8"))


def _save_token(creds: Any, token_path: Path) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")


def _credentials_path() -> Path:
    return Path(os.getenv("GMAIL_CREDENTIALS_FILE", str(DEFAULT_CREDENTIALS_FILE)))


def _token_path() -> Path:
    return Path(os.getenv("GMAIL_TOKEN_FILE", str(DEFAULT_TOKEN_FILE)))

from __future__ import annotations

import argparse
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send report email")
    parser.add_argument("--report", type=str, required=True, help="Path to markdown report")
    parser.add_argument("--to", type=str, default=None, help="Recipient email override")
    parser.add_argument("--subject", type=str, default="每日论文简版", help="Email subject")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        raise SystemExit(f"Report file not found: {report_path}")

    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "465").strip())
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    smtp_ssl = os.getenv("SMTP_SSL", "true").strip().lower() not in {"0", "false", "no"}
    from_email = os.getenv("FROM_EMAIL", smtp_user).strip()
    to_email = (args.to or os.getenv("TO_EMAIL", "")).strip()

    if not smtp_host or not smtp_user or not smtp_pass or not from_email or not to_email:
        raise SystemExit(
            "Missing SMTP config. Require SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS/FROM_EMAIL/TO_EMAIL"
        )

    body = report_path.read_text(encoding="utf-8")

    msg = EmailMessage()
    msg["Subject"] = args.subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(body)

    if smtp_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

    print("Email sent to:", to_email)
    print("Report:", report_path)


if __name__ == "__main__":
    main()

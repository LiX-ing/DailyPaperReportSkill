from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests


def load_card_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_feishu_interactive_message(payload: dict[str, Any]) -> dict[str, Any]:
    paper = payload.get("paper", {}) if isinstance(payload.get("paper"), dict) else {}
    card = payload.get("card", {}) if isinstance(payload.get("card"), dict) else {}
    base = card.get("基础信息", {}) if isinstance(card.get("基础信息"), dict) else {}
    professional = card.get("专业分析", {}) if isinstance(card.get("专业分析"), dict) else {}
    reading = card.get("阅读建议", {}) if isinstance(card.get("阅读建议"), dict) else {}

    title = str(base.get("中文标题") or paper.get("title") or "每日论文速读卡片")
    year = str(base.get("发表年份") or paper.get("year") or "未提供")
    venue = str(base.get("发表载体") or paper.get("venue") or "未提供")
    abstract = str(card.get("摘要中文精译") or "未提供")
    contributions = str(professional.get("核心贡献") or "未提供")
    decision = str(reading.get("是否建议精读") or "未提供")
    url = str(paper.get("url") or "")
    doi = str(paper.get("doi") or "")

    lines = [
        f"**年份**: {year}",
        f"**发表载体**: {venue}",
        "",
        "**摘要中文精译**",
        abstract,
        "",
        "**核心贡献**",
        contributions,
        "",
        "**阅读建议**",
        decision,
    ]
    if url:
        lines.extend(["", f"[论文链接]({url})"])
    if doi:
        lines.append(f"DOI: {doi}")

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue",
            },
            "elements": [
                {"tag": "markdown", "content": "\n".join(lines)},
            ],
        },
    }


def send_feishu_webhook(webhook_url: str, card_payload: dict[str, Any], timeout: int = 15) -> requests.Response:
    message = _to_feishu_interactive_message(card_payload)
    resp = requests.post(
        webhook_url,
        json=message,
        headers={"Content-Type": "application/json"},
        timeout=timeout,
    )
    resp.raise_for_status()
    # Feishu webhook may return HTTP 200 but business-level non-zero error code.
    try:
        data = resp.json()
    except ValueError:
        return resp
    status_code = data.get("StatusCode", data.get("code", 0))
    if status_code not in (0, "0", None):
        msg = data.get("StatusMessage") or data.get("msg") or "unknown feishu webhook error"
        raise RuntimeError(f"Feishu webhook business error: code={status_code}, msg={msg}")
    return resp


def send_feishu_webhook_from_file(webhook_url: str, card_json_path: Path, timeout: int = 15) -> requests.Response:
    payload = load_card_payload(card_json_path)
    return send_feishu_webhook(webhook_url=webhook_url, card_payload=payload, timeout=timeout)

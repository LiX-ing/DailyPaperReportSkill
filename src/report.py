from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re
from typing import Any

from .openalex_client import Paper


def _slugify_title(title: str) -> str:
    s = title.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return (s[:80]).strip("-")


def _next_available(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    idx = 2
    while True:
        candidate = parent / f"{stem}-{idx}{suffix}"
        if not candidate.exists():
            return candidate
        idx += 1


def _resolve_output_path(out_dir: Path, paper: Paper, domain: str, query_mode: bool, suffix: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    default_filename = f"{today}-{domain}-paper{suffix}"
    default_path = out_dir / default_filename

    if query_mode and default_path.exists():
        slug = _slugify_title(paper.title)
        if not slug:
            slug = "paper"
        path = _next_available(out_dir / f"{today}-{slug}{suffix}")
    else:
        path = default_path
    return path


def write_markdown_report(
    out_dir: Path,
    paper: Paper,
    summary: dict[str, Any],
    domain: str,
    query_mode: bool = False,
) -> Path:
    path = _resolve_output_path(
        out_dir=out_dir,
        paper=paper,
        domain=domain,
        query_mode=query_mode,
        suffix=".md",
    )

    card_markdown = summary.get("card_markdown")
    if not card_markdown:
        payload = summary.get("card_payload")
        if isinstance(payload, dict):
            base = payload.get("基础信息", {}) if isinstance(payload.get("基础信息"), dict) else {}
            one_liner = payload.get("一句话定位", "未提供")
            zh_abs = payload.get("摘要中文精译", summary.get("zh_abstract", "未提供"))
            novice = payload.get("小白友好解读", {})
            professional = payload.get("专业分析", {})
            reading = payload.get("阅读建议", {})
        else:
            base = {}
            one_liner = "未提供"
            zh_abs = summary.get("zh_abstract", "未提供")
            novice = {}
            professional = {}
            reading = {}

        def _dict_lines(obj: Any) -> str:
            if not isinstance(obj, dict) or not obj:
                return "- 未提供"
            lines: list[str] = []
            for k, v in obj.items():
                if isinstance(v, list):
                    if v:
                        lines.append(f"- {k}:")
                        for i, item in enumerate(v, start=1):
                            lines.append(f"  {i}) {item}")
                    else:
                        lines.append(f"- {k}: 未提供")
                else:
                    lines.append(f"- {k}: {v}")
            return "\n".join(lines)

        card_markdown = (
            "### 论文链接\n"
            f"- 论文链接: {paper.url or '未提供'}\n"
            f"- DOI: {paper.doi or '未提供'}\n\n"
            "### 基础信息\n"
            f"- 中文标题: {base.get('中文标题', summary.get('zh_title', '未提供'))}\n"
            f"- 发表时间: {base.get('发表时间', '未提供')}\n"
            f"- 发表年份: {base.get('发表年份', str(paper.year))}\n"
            f"- 研究领域: {base.get('研究领域', '未提供')}\n"
            f"- 论文类型: {base.get('论文类型', '未提供')}\n"
            f"- 发表载体: {base.get('发表载体', paper.venue or '未提供')}\n"
            f"- 作者: {base.get('作者', '未提供')}\n"
            f"- 研究机构: {base.get('研究机构', '未提供')}\n\n"
            "### 一句话定位\n"
            f"{one_liner}\n\n"
            "### 摘要中文精译\n"
            f"{zh_abs}\n\n"
            "### 小白友好解读\n"
            f"{_dict_lines(novice)}\n\n"
            "### 专业分析\n"
            f"{_dict_lines(professional) if isinstance(professional, dict) and professional else '- 核心贡献: ' + str(summary.get('key_points', '未提供'))}\n\n"
            "### 阅读建议\n"
            f"{_dict_lines(reading) if isinstance(reading, dict) and reading else '- 是否建议精读: ' + str(summary.get('decision', '未提供'))}"
        )

    content = f"""# 结构化速读卡片（{domain}）

{card_markdown}
"""
    path.write_text(content, encoding="utf-8")
    return path


def write_feishu_card_json(
    out_dir: Path,
    paper: Paper,
    summary: dict[str, Any],
    domain: str,
    query_mode: bool = False,
) -> Path:
    path = _resolve_output_path(
        out_dir=out_dir,
        paper=paper,
        domain=domain,
        query_mode=query_mode,
        suffix=".json",
    )
    payload = summary.get("card_payload")
    if not isinstance(payload, dict):
        payload = {
            "基础信息": {
                "中文标题": summary.get("zh_title", ""),
                "发表年份": str(paper.year),
                "发表载体": paper.venue or "未提供",
            },
            "摘要中文精译": summary.get("zh_abstract", ""),
            "专业分析": {"核心贡献": summary.get("key_points", "")},
            "阅读建议": {"是否建议精读": summary.get("decision", "")},
        }
    card_doc = {
        "schema_version": "v1",
        "domain": domain,
        "paper": {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "url": paper.url,
            "doi": paper.doi,
            "year": paper.year,
            "venue": paper.venue,
        },
        "card": payload,
    }
    path.write_text(json.dumps(card_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

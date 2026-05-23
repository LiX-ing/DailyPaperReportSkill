from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .llm import BaseLLMClient
from .openalex_client import Paper
from .prompt_loader import render_prompt


def _word_count(text: str) -> int:
    return len([w for w in text.strip().split() if w])


def _format_card_markdown(data: dict[str, Any], paper_url: str, paper_doi: str) -> str:
    lines: list[str] = []
    lines.append("### 论文链接")
    lines.append(f"- 论文链接: {paper_url or '未提供'}")
    lines.append(f"- DOI: {paper_doi or '未提供'}")

    base = data.get("基础信息", {})
    if isinstance(base, dict):
        lines.append("### 基础信息")
        for k in [
            "中文标题",
            "发表时间",
            "发表年份",
            "研究领域",
            "论文类型",
            "发表载体",
            "作者",
            "研究机构",
        ]:
            v = base.get(k, "未提供")
            if isinstance(v, list):
                v = "；".join(str(x) for x in v) if v else "未提供"
            lines.append(f"- {k}: {v}")

    def _append_obj(title: str, obj: Any) -> None:
        if not isinstance(obj, dict):
            return
        lines.append(f"### {title}")
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

    one_liner = data.get("一句话定位")
    if one_liner:
        lines.append("### 一句话定位")
        lines.append(str(one_liner))

    translated = data.get("摘要中文精译")
    if translated:
        lines.append("### 摘要中文精译")
        lines.append(str(translated))

    _append_obj("小白友好解读", data.get("小白友好解读"))
    _append_obj("专业分析", data.get("专业分析"))
    _append_obj("阅读建议", data.get("阅读建议"))
    return "\n".join(lines).strip()


def _parse_llm_json(text: str, paper_url: str, paper_doi: str) -> dict[str, Any] | None:
    raw = text.strip()
    candidates = [raw]
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        candidates.append(match.group(0))

    for c in candidates:
        try:
            data = json.loads(c)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue

        # V1 schema (flat english keys)
        zh_title = str(data.get("zh_title", "")).strip()
        zh_abs = str(data.get("zh_abstract_3sentences", "")).strip()
        key_points = data.get("key_points", [])
        decision = str(data.get("decision", "")).strip()
        decision_reason = str(data.get("decision_reason", "")).strip()

        # V2 schema (nested Chinese keys)
        if not (zh_title or zh_abs):
            base_info = data.get("基础信息", {})
            if isinstance(base_info, dict):
                zh_title = str(base_info.get("中文标题", "")).strip()
            zh_abs = str(data.get("摘要中文精译", "")).strip()
            professional = data.get("专业分析", {})
            if isinstance(professional, dict):
                key_points = professional.get("核心贡献", [])
            reading = data.get("阅读建议", {})
            if isinstance(reading, dict):
                decision = str(reading.get("是否建议精读", "")).strip()
                decision_reason = str(reading.get("建议理由", "")).strip()

        if isinstance(key_points, list):
            key_points_text = "\n".join(
                f"{i+1}) {str(k).strip()}" for i, k in enumerate(key_points[:3]) if str(k).strip()
            )
        else:
            key_points_text = str(key_points).strip()

        decision_text = decision if not decision_reason else f"{decision}：{decision_reason}"

        if zh_title or zh_abs or key_points_text:
            result: dict[str, Any] = {
                "zh_title": zh_title,
                "zh_abstract": zh_abs,
                "key_points": key_points_text,
                "decision": decision_text,
                "summary_mode": "llm",
            }
            if isinstance(data.get("基础信息"), dict):
                result["summary_schema"] = "v2_card"
                result["card_markdown"] = _format_card_markdown(
                    data=data,
                    paper_url=paper_url,
                    paper_doi=paper_doi,
                )
                result["card_payload"] = data
            return result
    return None


def summarize_zh(
    paper: Paper,
    abstract_min_words: int,
    llm_client: BaseLLMClient,
    prompt_template_path: Path,
) -> dict[str, str]:
    abstract = (paper.abstract or "").strip()
    if not abstract:
        abstract = "No abstract available."

    if _word_count(abstract) < abstract_min_words:
        return {
            "zh_title": f"{paper.title}（中文标题待生成）",
            "zh_abstract": "摘要较短，建议进入 PDF 全文总结流程。",
            "key_points": "1) 需要全文抓取\n2) 需要章节级总结\n3) 建议人工二次校验",
            "decision": "待定（摘要信息不足）",
            "summary_mode": "local_fallback",
        }

    prompt = render_prompt(
        template_path=prompt_template_path,
        variables={
            "title": paper.title,
            "venue": paper.venue,
            "venue_type": "未知",
            "pub_date": "未提供",
            "authors": "未提供",
            "affiliations": "未提供",
            "year": str(paper.year),
            "abstract": abstract,
        },
    )

    text = llm_client.generate(prompt).strip()
    if not text:
        return {
            "zh_title": f"{paper.title}（待翻译）",
            "zh_abstract": (
                "当前为本地降级模式，未成功调用 LLM。以下附英文摘要片段供快速浏览：\n"
                f"{abstract[:500]}"
            ),
            "key_points": "1) 已成功检索到目标论文\n2) 摘要翻译与总结未成功调用模型\n3) 请检查 LLM_PROVIDER/LLM_MODEL/LLM_BASE_URL",
            "decision": "暂不精读：先修复模型配置后再生成中文总结",
            "summary_mode": "local_fallback",
        }

    parsed = _parse_llm_json(text, paper.url, paper.doi)
    if parsed:
        if not parsed.get("zh_title"):
            parsed["zh_title"] = f"{paper.title}（待翻译）"
        return parsed

    return {
        "zh_title": f"{paper.title}（待翻译）",
        "zh_abstract": text,
        "key_points": "1) 模型返回非结构化文本\n2) 已原样保留输出\n3) 可调整 prompt 强约束 JSON 输出",
        "decision": "建议精读摘要后决定",
        "summary_mode": "llm_unstructured",
    }

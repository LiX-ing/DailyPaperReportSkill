from __future__ import annotations

import argparse
import os
import random
from datetime import date
from pathlib import Path
import traceback

import requests
from dotenv import load_dotenv

from .config import load_skill_config, load_venues_config
from .feishu_sender import send_feishu_webhook_from_file
from .llm import build_llm_client, load_llm_settings
from .openalex_client import fetch_candidates, match_by_venues
from .openreview_client import fetch_candidates_openreview
from .query_planner import build_query_plan
from .report import write_feishu_card_json, write_markdown_report
from .scorer import rank_papers
from .semantic_scholar_client import fetch_candidates_semantic_scholar
from .source_capabilities import get_capability
from .storage import SeenPaperStore
from .summarizer import summarize_zh


def _env_bool(name: str) -> bool | None:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return None
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily paper Chinese summary MVP")
    parser.add_argument(
        "--domain",
        type=str,
        default="ai",
        help="Domain key in config/venues.yaml",
    )
    parser.add_argument(
        "--year-window",
        type=int,
        default=None,
        help="Years window, overrides config",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use a local mock paper and skip network calls",
    )
    parser.add_argument(
        "--prompt-template",
        type=str,
        default="prompts/zh_summary_prompt.txt",
        help="Prompt template path relative to project root or absolute path",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print debug counts for fetched/matched candidates",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=os.getenv("PAPER_SOURCE", "openalex"),
        choices=["openalex", "semantic_scholar", "openreview"],
        help="Paper metadata source",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="Natural language query to constrain year/domain/venue",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not persist markdown report to output/",
    )
    parser.add_argument(
        "--skill-config",
        type=str,
        default="config/skill.yaml",
        help="Skill runtime config path relative to project root or absolute path",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()

    root = Path(__file__).resolve().parents[1]
    cfg = load_venues_config(root / "config" / "venues.yaml")

    args = parse_args()
    prompt_template_path = Path(args.prompt_template)
    if not prompt_template_path.is_absolute():
        prompt_template_path = root / prompt_template_path
    if not prompt_template_path.exists():
        raise SystemExit(f"Prompt template not found: {prompt_template_path}")
    skill_config_path = Path(args.skill_config)
    if not skill_config_path.is_absolute():
        skill_config_path = root / skill_config_path
    if not skill_config_path.exists():
        raise SystemExit(f"Skill config not found: {skill_config_path}")
    skill_cfg = load_skill_config(skill_config_path)
    # Auto-bind sibling credentials file for skill runs unless explicitly overridden.
    if not os.getenv("SKILL_CREDENTIALS_PATH", "").strip():
        sibling_credentials = skill_config_path.parent / "credentials.yaml"
        if sibling_credentials.exists():
            os.environ["SKILL_CREDENTIALS_PATH"] = str(sibling_credentials)

    plan = build_query_plan(
        query=args.query,
        default_domain=args.domain,
        cfg_domains=cfg.domains,
        venue_aliases=cfg.venue_aliases,
    )
    requested_domain = plan.domain
    requested_venue = plan.venue
    requested_year = plan.year

    domain_cfg = cfg.domains.get(requested_domain)
    if not domain_cfg:
        available = ", ".join(cfg.domains.keys())
        raise SystemExit(f"Unknown domain: {requested_domain}. Available: {available}")

    selection_cfg = cfg.selection
    year_window = args.year_window or selection_cfg.get("default_year_window", 2)
    current_year = date.today().year
    if requested_year is not None:
        if requested_year > current_year:
            raise SystemExit(
                f"Requested year {requested_year} is in the future (today: {current_year})."
            )
        year_window = max(1, current_year - requested_year + 1)
    elif plan.year_start is not None and plan.year_end is not None:
        year_window = max(1, current_year - plan.year_start + 1)
    max_candidates = selection_cfg.get("max_candidates", 50)
    abstract_min_words = selection_cfg.get("abstract_min_words", 80)
    llm_settings = load_llm_settings(root=root)
    llm_client = build_llm_client(llm_settings)
    verify_ssl = os.getenv("VERIFY_SSL", "true").strip().lower() not in {
        "0",
        "false",
        "no",
    }
    auto_fallback = os.getenv("AUTO_FALLBACK", "true").strip().lower() not in {
        "0",
        "false",
        "no",
    }
    allow_cache_fallback = os.getenv("ALLOW_CACHE_FALLBACK", "true").strip().lower() not in {
        "0",
        "false",
        "no",
    }
    store = SeenPaperStore(root / "data" / "seen_papers.db")
    output_cfg = skill_cfg.output
    dedup_cfg = skill_cfg.dedup
    output_formats = output_cfg.get("formats", ["markdown"])
    md_dir = root / output_cfg.get("md_dir", "output/md")
    feishu_card_dir = root / output_cfg.get("feishu_card_dir", "output/feishu_cards")
    dedup_enabled = bool(dedup_cfg.get("enabled", True))
    skip_if_generated = bool(dedup_cfg.get("skip_if_generated", True))
    feishu_webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
    webhook_cfg = skill_cfg.raw.get("webhook", {}) if isinstance(skill_cfg.raw, dict) else {}
    webhook_enabled_by_config = bool(webhook_cfg.get("enabled", False))
    webhook_url_by_config = str(webhook_cfg.get("url", "")).strip()
    webhook_enabled_by_env = _env_bool("ENABLE_FEISHU_WEBHOOK")
    webhook_enabled = (
        webhook_enabled_by_env if webhook_enabled_by_env is not None else webhook_enabled_by_config
    )
    if not feishu_webhook_url:
        feishu_webhook_url = webhook_url_by_config
    webhook_url_source = "env" if os.getenv("FEISHU_WEBHOOK_URL", "").strip() else ("config" if webhook_url_by_config else "none")

    target_venues = plan.target_venues or domain_cfg.get("venues", [])
    source_cap = get_capability(args.source)
    source_query_text = plan.source_query_text if source_cap.supports_query_text else ""

    papers = []
    fetch_error: Exception | None = None
    if args.dry_run:
        from .openalex_client import Paper

        papers = [
            Paper(
                paper_id="mock:001",
                title="A Mock Paper for Daily Pipeline Check",
                abstract=(
                    "This paper proposes a mock method for testing daily "
                    "research reading pipelines with minimal setup."
                ),
                year=2026,
                venue="NeurIPS",
                venue_candidates=["NeurIPS", "Neural Information Processing Systems"],
                doi="",
                url="https://example.org/mock-paper",
            )
        ]
    else:
        try:
            if args.source == "openalex":
                papers = fetch_candidates(
                    year_window=year_window,
                    max_candidates=max_candidates,
                    venues=target_venues,
                    venue_aliases=cfg.venue_aliases,
                    email=os.getenv("OPENALEX_EMAIL", "").strip() or None,
                    api_key=os.getenv("OPENALEX_API_KEY", "").strip() or None,
                    verify_ssl=verify_ssl,
                )
            elif args.source == "openreview":
                papers = fetch_candidates_openreview(
                    year_window=year_window,
                    max_candidates=max_candidates,
                    venue_templates=domain_cfg.get("openreview_venues", []),
                    base_url=os.getenv("OPENREVIEW_BASE_URL", "https://api2.openreview.net"),
                    verify_ssl=verify_ssl,
                )
            else:
                papers = fetch_candidates_semantic_scholar(
                    year_window=year_window,
                    max_candidates=max_candidates,
                    venues=target_venues,
                    query_text=source_query_text,
                    api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip() or None,
                    verify_ssl=verify_ssl,
                )
        except requests.RequestException as e:
            fetch_error = e
            papers = []
            if args.verbose:
                print(f"{args.source} request failed. Details: {e}")
    matched = match_by_venues(
        papers,
        target_venues,
        venue_aliases=cfg.venue_aliases,
    )
    if requested_year is not None:
        matched = [p for p in matched if p.year == requested_year]
    elif plan.year_start is not None and plan.year_end is not None:
        matched = [p for p in matched if plan.year_start <= p.year <= plan.year_end]
    if not matched and (not args.dry_run) and allow_cache_fallback and fetch_error is not None:
        cached = store.load_cache(limit=2000)
        cache_matched = match_by_venues(
            cached,
            target_venues,
            venue_aliases=cfg.venue_aliases,
        )
        if requested_year is not None:
            cache_matched = [p for p in cache_matched if p.year == requested_year]
        elif plan.year_start is not None and plan.year_end is not None:
            cache_matched = [p for p in cache_matched if plan.year_start <= p.year <= plan.year_end]
        if cache_matched:
            matched = cache_matched
            papers = cache_matched
            if args.verbose:
                print("Using local cache fallback due to source request failure.")
    if not matched and (not args.dry_run) and args.source == "openalex" and auto_fallback:
        # Fallback when OpenAlex candidates are dominated by repository-only records.
        try:
            papers_fallback = fetch_candidates_semantic_scholar(
                year_window=year_window,
                max_candidates=max_candidates,
                venues=target_venues,
                query_text=source_query_text,
                api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip() or None,
                verify_ssl=verify_ssl,
            )
            matched = match_by_venues(
                papers_fallback,
                target_venues,
                venue_aliases=cfg.venue_aliases,
            )
            if requested_year is not None:
                matched = [p for p in matched if p.year == requested_year]
            elif plan.year_start is not None and plan.year_end is not None:
                matched = [p for p in matched if plan.year_start <= p.year <= plan.year_end]
            if matched:
                papers = papers_fallback
                if args.verbose:
                    print("OpenAlex matched 0. Auto-fallback to semantic_scholar succeeded.")
        except requests.RequestException as e:
            if args.verbose:
                print(
                    "OpenAlex matched 0 and semantic_scholar fallback failed.",
                    f"Details: {e}",
                )
            try:
                papers_fallback_2 = fetch_candidates_openreview(
                    year_window=year_window,
                    max_candidates=max_candidates,
                    venue_templates=domain_cfg.get("openreview_venues", []),
                    base_url=os.getenv("OPENREVIEW_BASE_URL", "https://api2.openreview.net"),
                    verify_ssl=verify_ssl,
                )
                matched = match_by_venues(
                    papers_fallback_2,
                    target_venues,
                    venue_aliases=cfg.venue_aliases,
                )
                if requested_year is not None:
                    matched = [p for p in matched if p.year == requested_year]
                elif plan.year_start is not None and plan.year_end is not None:
                    matched = [p for p in matched if plan.year_start <= p.year <= plan.year_end]
                if matched:
                    papers = papers_fallback_2
                    if args.verbose:
                        print("OpenAlex->Semantic failed. Auto-fallback to openreview succeeded.")
            except requests.RequestException as e2:
                if args.verbose:
                    print("OpenReview fallback failed.", f"Details: {e2}")
    if args.verbose:
        print("Source:", args.source)
        print("Resolved domain:", requested_domain)
        print("Resolved venue:", requested_venue or "(none)")
        print("Resolved year:", requested_year or "(none)")
        print("Resolved year range:", f"{plan.year_start}-{plan.year_end}" if plan.year_start else "(none)")
        print("Query keywords:", ", ".join(plan.keywords) if plan.keywords else "(none)")
        print("Should persist:", (not args.no_save) and plan.should_persist)
        print("SSL verify:", verify_ssl)
        print("Auto fallback:", auto_fallback)
        print("Cache fallback:", allow_cache_fallback)
        print("LLM provider:", llm_settings.provider)
        print("LLM model:", llm_settings.model)
        print("Webhook enabled:", webhook_enabled)
        print("Webhook url source:", webhook_url_source)
        print("Webhook url present:", bool(feishu_webhook_url))
        print("Fetched candidates:", len(papers))
        print("Matched by venues:", len(matched))
        if not matched:
            sample_venues = []
            for p in papers:
                if p.venue and p.venue not in sample_venues:
                    sample_venues.append(p.venue)
                if len(sample_venues) >= 15:
                    break
            if sample_venues:
                print("Sample venues from fetched data:")
                for v in sample_venues:
                    print("-", v)

    if not matched:
        if fetch_error is not None and allow_cache_fallback:
            store.close()
            raise SystemExit(
                "No matched papers found. Source request failed and local cache had no match. "
                "Try changing source/domain/venue or run once with network available."
            )
        store.close()
        raise SystemExit("No matched papers found. Try expanding venues list.")
    webhook_delivery_status = "not_configured"
    webhook_delivery_error = ""
    try:
        if papers:
            store.upsert_cache(papers)
        if plan.has_constraints:
            ranked = rank_papers(matched, plan=plan, venue_aliases=cfg.venue_aliases)
            ranked_papers = [item.paper for item in ranked]
            unseen_ranked = [
                p
                for p in ranked_papers
                if not store.exists(p.paper_id)
                and not (dedup_enabled and skip_if_generated and store.was_generated(p.paper_id))
            ]
            picked = unseen_ranked[0] if unseen_ranked else ranked_papers[0]
        else:
            unseen = [
                p
                for p in matched
                if not store.exists(p.paper_id)
                and not (dedup_enabled and skip_if_generated and store.was_generated(p.paper_id))
            ]
            picked = random.choice(unseen or matched)

        summary = summarize_zh(
            paper=picked,
            abstract_min_words=abstract_min_words,
            llm_client=llm_client,
            prompt_template_path=prompt_template_path,
        )

        should_save = (not args.no_save) and plan.should_persist
        report_md = None
        report_feishu = None
        if should_save:
            if "markdown" in output_formats:
                report_md = write_markdown_report(
                    out_dir=md_dir,
                    paper=picked,
                    summary=summary,
                    domain=requested_domain,
                    query_mode=bool(args.query.strip()),
                )
            if "feishu_card_json" in output_formats:
                report_feishu = write_feishu_card_json(
                    out_dir=feishu_card_dir,
                    paper=picked,
                    summary=summary,
                    domain=requested_domain,
                    query_mode=bool(args.query.strip()),
                )
                if feishu_webhook_url and webhook_enabled:
                    try:
                        send_feishu_webhook_from_file(
                            webhook_url=feishu_webhook_url,
                            card_json_path=report_feishu,
                        )
                        webhook_delivery_status = "delivered"
                    except Exception as e:  # pragma: no cover - defensive runtime guard
                        webhook_delivery_status = "failed"
                        webhook_delivery_error = str(e)
                        if args.verbose:
                            traceback.print_exc()

        store.add(picked.paper_id, picked.title)
        if should_save:
            store.add_generated_record(
                paper_id=picked.paper_id,
                title=picked.title,
                source=args.source,
                md_path=str(report_md) if report_md else None,
                feishu_card_path=str(report_feishu) if report_feishu else None,
                status="success",
            )

        print("Paper selected:", picked.title)
        print("Venue:", picked.venue)
        print("LLM provider:", llm_settings.provider)
        if report_md is not None:
            print("Markdown report:", report_md)
        if report_feishu is not None:
            print("Feishu card JSON:", report_feishu)
            if feishu_webhook_url and webhook_enabled:
                if webhook_delivery_status == "delivered":
                    print("Feishu webhook: delivered")
                elif webhook_delivery_status == "failed":
                    print("Feishu webhook: failed (non-blocking)")
                    print("Feishu webhook error:", webhook_delivery_error)
                else:
                    print("Feishu webhook: skipped")
            elif not webhook_enabled:
                print("Feishu webhook: skipped (ENABLE_FEISHU_WEBHOOK is false)")
            else:
                print("Feishu webhook: skipped (webhook url not set)")
        if report_md is None and report_feishu is None:
            if should_save:
                print("Report: no output generated (check output.formats in skill config)")
            else:
                print("Report: skipped (--no-save or query requested no-save)")
    finally:
        store.close()


if __name__ == "__main__":
    main()

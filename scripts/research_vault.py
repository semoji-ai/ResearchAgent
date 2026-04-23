#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ResearchTopicPaths:
    research_root: Path
    topic: str
    topic_slug: str
    raw_slug: str
    raw_topic_dir: Path
    manifests_dir: Path
    wiki_dir: Path
    topic_snapshot_path: Path
    specialist_report_path: Path
    executive_summary_path: Path


RUN_STAGES = (
    "question-refinement",
    "search-planning",
    "parallel-collection",
    "cross-verification",
    "knowledge-synthesis",
    "quality-assurance",
    "packaging",
)

RUN_STATUSES = (
    "active",
    "blocked",
    "completed",
)

SOURCE_QUALITY_GRADES = (
    "A",
    "B",
    "C",
    "D",
    "E",
)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    vault_dir = _effective_vault_dir(args.vault_dir)

    if args.command == "init-topic":
        payload = ensure_research_topic(
            args.topic,
            topic_slug=_optional_text(args.topic_slug),
            vault_dir=vault_dir,
        )
    elif args.command == "start-run":
        payload = start_research_run(
            args.topic,
            run_id=_optional_text(args.run_id),
            query=args.query,
            focus=args.focus,
            planned_agents=args.agent,
            notes=args.notes,
            topic_slug=_optional_text(args.topic_slug),
            entity_slug=_optional_text(args.entity_slug),
            section_slug=_optional_text(args.section_slug),
            vault_dir=vault_dir,
        )
    elif args.command == "set-run-stage":
        payload = set_run_stage(
            args.topic,
            run_id=args.run_id,
            stage=args.stage,
            status=args.status,
            notes=args.notes,
            mark_complete=args.mark_complete,
            topic_slug=_optional_text(args.topic_slug),
            vault_dir=vault_dir,
        )
    elif args.command == "register-source":
        payload = register_source_note(
            args.topic,
            run_id=args.run_id,
            title=args.title,
            source_url=args.source_url,
            note_markdown=_load_body(args.body, args.body_file),
            source_kind=args.source_kind,
            source_id=_optional_text(args.source_id),
            author=args.author,
            published_at=args.published_at,
            captured_at=args.captured_at,
            language=args.language,
            license_name=args.license_name,
            quality_grade=args.quality_grade,
            summary=args.summary,
            key_points=args.key_point,
            tags=args.tag,
            source_class=args.source_class,
            trust_tier=args.trust_tier,
            trust_score=args.trust_score,
            domain=args.domain,
            tier_reason=args.tier_reason,
            publisher_resolved=args.publisher_resolved,
            lane_id=args.lane_id,
            discovery_confidence=args.discovery_confidence,
            discovered_via_query=args.discovered_via_query,
            discovery_stage=args.discovery_stage,
            relevance_score=args.relevance_score,
            relevance_band=args.relevance_band,
            ranking_score=args.ranking_score,
            topic_slug=_optional_text(args.topic_slug),
            vault_dir=vault_dir,
        )
    elif args.command == "register-image":
        payload = register_image_note(
            args.topic,
            run_id=args.run_id,
            title=args.title,
            source_url=args.source_url,
            caption=args.caption,
            note_markdown=_load_body(args.body, args.body_file),
            image_id=_optional_text(args.image_id),
            asset_url=args.asset_url,
            asset_file_path=args.asset_file,
            creator=args.creator,
            creator_url=args.creator_url,
            license_name=args.license_name,
            license_url=args.license_url,
            attribution_text=args.attribution_text,
            copyright_notice=args.copyright_notice,
            mime_type=args.mime_type,
            relevance=args.relevance,
            linked_claim_ids=args.linked_claim_id,
            linked_pages=args.linked_page,
            tags=args.tag,
            topic_slug=_optional_text(args.topic_slug),
            vault_dir=vault_dir,
        )
    elif args.command == "ingest-packet":
        payload = ingest_packet(
            args.topic,
            run_id=args.run_id,
            packet_path=Path(args.packet_file).expanduser().resolve(),
            topic_slug=_optional_text(args.topic_slug),
            vault_dir=vault_dir,
            refresh_after_ingest=args.refresh,
        )
    elif args.command == "append-claim":
        payload = append_claim(
            args.topic,
            claim=args.claim,
            source_ids=args.source_id,
            run_id=args.run_id,
            claim_id=_optional_text(args.claim_id),
            kind=args.kind,
            confidence=args.confidence,
            evidence=args.evidence,
            counterpoints=args.counterpoint,
            linked_pages=args.linked_page,
            status=args.status,
            topic_slug=_optional_text(args.topic_slug),
            vault_dir=vault_dir,
        )
    elif args.command == "append-question":
        payload = append_open_question(
            args.topic,
            question=args.question,
            question_id=_optional_text(args.question_id),
            priority=args.priority,
            owner=args.owner,
            context=args.context,
            related_claim_ids=args.related_claim_id,
            topic_slug=_optional_text(args.topic_slug),
            vault_dir=vault_dir,
        )
    elif args.command == "refresh-topic":
        payload = refresh_topic_snapshot(
            args.topic,
            topic_slug=_optional_text(args.topic_slug),
            vault_dir=vault_dir,
        )
    elif args.command == "lint-topic":
        payload = lint_research_topic(
            args.topic,
            topic_slug=_optional_text(args.topic_slug),
            vault_dir=vault_dir,
        )
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research_vault.py",
        description="Manage llm-wiki research artifacts inside a user-configured research root.",
    )
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init-topic", help="Initialize a topic scaffold")
    _add_topic_args(init_parser)

    run_parser = subparsers.add_parser("start-run", help="Create a raw run scaffold")
    _add_topic_args(run_parser)
    run_parser.add_argument("--run-id", default="", help="Optional explicit run id")
    run_parser.add_argument("--entity-slug", default="", help="Optional canonical entity slug for raw run storage")
    run_parser.add_argument("--section-slug", default="", help="Optional section slug recorded in run metadata")
    run_parser.add_argument("--query", default="", help="Search or planning query for the run")
    run_parser.add_argument("--focus", action="append", default=[], help="Optional focus item; repeatable")
    run_parser.add_argument("--agent", action="append", default=[], help="Optional planned agent label; repeatable")
    run_parser.add_argument("--notes", default="", help="Optional note stored in the run manifest")

    stage_parser = subparsers.add_parser("set-run-stage", help="Update run stage/status for resumable sessions")
    _add_topic_args(stage_parser)
    stage_parser.add_argument("--run-id", required=True)
    stage_parser.add_argument("--stage", required=True, choices=RUN_STAGES, help="Current stage name")
    stage_parser.add_argument("--status", default="active", choices=RUN_STATUSES, help="Run status")
    stage_parser.add_argument("--notes", default="", help="Optional stage note")
    stage_parser.add_argument("--mark-complete", action="store_true", help="Mark the stage as completed")

    source_parser = subparsers.add_parser("register-source", help="Register a source note")
    _add_topic_args(source_parser)
    source_parser.add_argument("--run-id", required=True)
    source_parser.add_argument("--title", required=True)
    source_parser.add_argument("--source-url", required=True)
    source_parser.add_argument("--source-kind", default="web")
    source_parser.add_argument("--source-id", default="")
    source_parser.add_argument("--author", default="")
    source_parser.add_argument("--published-at", default="")
    source_parser.add_argument("--captured-at", default="")
    source_parser.add_argument("--language", default="")
    source_parser.add_argument("--license-name", default="")
    source_parser.add_argument("--quality-grade", default="", help="Optional source quality grade A-E")
    source_parser.add_argument("--summary", default="")
    source_parser.add_argument("--key-point", action="append", default=[], help="Key point; repeatable")
    source_parser.add_argument("--tag", action="append", default=[], help="Optional tag; repeatable")
    source_parser.add_argument("--source-class", default="", help="Optional source classification such as academic or institutional")
    source_parser.add_argument("--trust-tier", default="", help="Optional trust tier such as highest, high, medium, or low")
    source_parser.add_argument("--trust-score", default="", help="Optional numeric trust score")
    source_parser.add_argument("--domain", default="", help="Optional normalized domain")
    source_parser.add_argument("--tier-reason", default="", help="Optional trust classification rationale")
    source_parser.add_argument("--publisher-resolved", default="", help="Optional resolved publisher/domain label")
    source_parser.add_argument("--lane-id", default="", help="Optional discovery lane identifier")
    source_parser.add_argument("--discovery-confidence", default="", help="Optional discovery confidence such as high, medium, or blocked")
    source_parser.add_argument("--discovered-via-query", default="", help="Optional query that discovered the source")
    source_parser.add_argument("--discovery-stage", default="", help="Optional discovery stage such as seed or expansion")
    source_parser.add_argument("--relevance-score", default="", help="Optional discovery relevance score")
    source_parser.add_argument("--relevance-band", default="", help="Optional relevance band such as low, medium, or high")
    source_parser.add_argument("--ranking-score", default="", help="Optional final discovery ranking score")
    source_parser.add_argument("--body", default="", help="Inline markdown body")
    source_parser.add_argument("--body-file", default="", help="Markdown body file")

    image_parser = subparsers.add_parser("register-image", help="Register an image note")
    _add_topic_args(image_parser)
    image_parser.add_argument("--run-id", required=True)
    image_parser.add_argument("--title", required=True)
    image_parser.add_argument("--source-url", required=True)
    image_parser.add_argument("--caption", required=True)
    image_parser.add_argument("--image-id", default="")
    image_parser.add_argument("--asset-url", default="", help="Direct downloadable image asset URL when different from source URL")
    image_parser.add_argument("--asset-file", default="", help="Local image file to copy into image_assets/")
    image_parser.add_argument("--creator", default="")
    image_parser.add_argument("--creator-url", default="")
    image_parser.add_argument("--license-name", default="")
    image_parser.add_argument("--license-url", default="")
    image_parser.add_argument("--attribution-text", default="")
    image_parser.add_argument("--copyright-notice", default="")
    image_parser.add_argument("--mime-type", default="", help="Optional explicit MIME type for the stored asset")
    image_parser.add_argument("--relevance", default="")
    image_parser.add_argument("--linked-claim-id", action="append", default=[], help="Linked claim id; repeatable")
    image_parser.add_argument("--linked-page", action="append", default=[], help="Linked wiki page label; repeatable")
    image_parser.add_argument("--tag", action="append", default=[], help="Optional tag; repeatable")
    image_parser.add_argument("--body", default="", help="Inline markdown body")
    image_parser.add_argument("--body-file", default="", help="Markdown body file")

    packet_parser = subparsers.add_parser(
        "ingest-packet",
        help="Ingest a structured subagent packet into durable research storage",
    )
    _add_topic_args(packet_parser)
    packet_parser.add_argument("--run-id", required=True)
    packet_parser.add_argument("--packet-file", required=True, help="JSON packet file to ingest")
    packet_parser.add_argument("--refresh", action="store_true", help="Refresh topic snapshot after ingest")

    claim_parser = subparsers.add_parser("append-claim", help="Append or update a claim")
    _add_topic_args(claim_parser)
    claim_parser.add_argument("--claim", required=True)
    claim_parser.add_argument("--claim-id", default="")
    claim_parser.add_argument("--run-id", default="")
    claim_parser.add_argument("--kind", default="fact")
    claim_parser.add_argument("--confidence", default="working")
    claim_parser.add_argument("--evidence", default="")
    claim_parser.add_argument("--status", default="active")
    claim_parser.add_argument("--source-id", action="append", default=[], help="Backing source id; repeatable")
    claim_parser.add_argument("--counterpoint", action="append", default=[], help="Counterpoint; repeatable")
    claim_parser.add_argument("--linked-page", action="append", default=[], help="Linked wiki page label; repeatable")

    question_parser = subparsers.add_parser("append-question", help="Append an open question")
    _add_topic_args(question_parser)
    question_parser.add_argument("--question", required=True)
    question_parser.add_argument("--question-id", default="")
    question_parser.add_argument("--priority", default="medium")
    question_parser.add_argument("--owner", default="")
    question_parser.add_argument("--context", default="")
    question_parser.add_argument("--related-claim-id", action="append", default=[], help="Related claim id; repeatable")

    refresh_parser = subparsers.add_parser("refresh-topic", help="Refresh the topic snapshot")
    _add_topic_args(refresh_parser)

    lint_parser = subparsers.add_parser("lint-topic", help="Check consistency of topic storage")
    _add_topic_args(lint_parser)

    return parser


def _add_topic_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--topic", required=True, help="Human-readable topic title")
    parser.add_argument("--topic-slug", default="", help="Optional stable topic slug override")
    parser.add_argument(
        "--root-dir",
        dest="vault_dir",
        default="",
        help="Optional research root override. Defaults to LLM_WIKI_RESEARCH_DIR.",
    )
    parser.add_argument(
        "--vault-dir",
        dest="vault_dir",
        default="",
        help="Legacy alias for --root-dir.",
    )


def research_root(vault_dir: Optional[Path] = None) -> Path:
    root = Path(vault_dir).expanduser().resolve() if vault_dir else _default_research_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_topic_paths(
    topic: str,
    *,
    topic_slug: Optional[str] = None,
    entity_slug: Optional[str] = None,
    vault_dir: Optional[Path] = None,
) -> ResearchTopicPaths:
    normalized_topic = str(topic).strip()
    if not normalized_topic:
        raise ValueError("`topic` is required.")
    slug = str(topic_slug).strip() if topic_slug else _safe_slug(normalized_topic)
    raw_slug = str(entity_slug).strip() if entity_slug else slug
    root = research_root(vault_dir=vault_dir)
    return ResearchTopicPaths(
        research_root=root,
        topic=normalized_topic,
        topic_slug=slug,
        raw_slug=raw_slug,
        raw_topic_dir=root / "raw" / raw_slug,
        manifests_dir=root / "manifests" / slug,
        wiki_dir=root / "wiki" / slug,
        topic_snapshot_path=root / "topics" / f"{slug}.md",
        specialist_report_path=root / "topics" / f"{slug}.specialist_report.json",
        executive_summary_path=root / "topics" / f"{slug}.executive_summary.md",
    )


def ensure_research_topic(
    topic: str,
    *,
    topic_slug: Optional[str] = None,
    vault_dir: Optional[Path] = None,
) -> dict[str, str]:
    paths = resolve_topic_paths(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    required_dirs = [
        paths.research_root / "raw",
        paths.research_root / "manifests",
        paths.research_root / "wiki",
        paths.research_root / "topics",
        paths.research_root / "methodology",
        paths.research_root / "sources",
        paths.raw_topic_dir,
        paths.manifests_dir,
        paths.wiki_dir,
    ]
    for directory in required_dirs:
        directory.mkdir(parents=True, exist_ok=True)

    for manifest_name in ["sources.jsonl", "images.jsonl", "claims.jsonl", "open_questions.jsonl", "runs.jsonl"]:
        _write_if_missing(paths.manifests_dir / manifest_name, "")

    _write_if_missing(paths.wiki_dir / "index.md", _topic_index_markdown(paths, counts=None))
    _write_if_missing(
        paths.wiki_dir / "overview.md",
        _wiki_page(
            title=f"{paths.topic} Overview",
            topic=paths.topic,
            topic_slug=paths.topic_slug,
            page_type="overview",
            body="## Summary\n- 조사 범위와 핵심 맥락을 정리하세요.\n\n## Current Understanding\n- 아직 정리되지 않았습니다.\n",
        ),
    )
    _write_if_missing(
        paths.wiki_dir / "claims.md",
        _wiki_page(
            title=f"{paths.topic} Claims",
            topic=paths.topic,
            topic_slug=paths.topic_slug,
            page_type="claims",
            body="## Claim Ledger\n- 아직 기록된 claim이 없습니다.\n",
        ),
    )
    _write_if_missing(
        paths.wiki_dir / "entities.md",
        _wiki_page(
            title=f"{paths.topic} Entities",
            topic=paths.topic,
            topic_slug=paths.topic_slug,
            page_type="entities",
            body="## Entities\n- 핵심 인물, 기관, 개념을 정리하세요.\n",
        ),
    )
    _write_if_missing(
        paths.wiki_dir / "timeline.md",
        _wiki_page(
            title=f"{paths.topic} Timeline",
            topic=paths.topic,
            topic_slug=paths.topic_slug,
            page_type="timeline",
            body="## Timeline\n- 중요한 연표가 아직 정리되지 않았습니다.\n",
        ),
    )
    _write_if_missing(
        paths.wiki_dir / "images.md",
        _wiki_page(
            title=f"{paths.topic} Images",
            topic=paths.topic,
            topic_slug=paths.topic_slug,
            page_type="images",
            body="## Image Ledger\n- 아직 기록된 이미지 자료가 없습니다.\n",
        ),
    )
    _write_if_missing(
        paths.wiki_dir / "questions.md",
        _wiki_page(
            title=f"{paths.topic} Questions",
            topic=paths.topic,
            topic_slug=paths.topic_slug,
            page_type="questions",
            body="## Open Questions\n- 아직 등록된 open question이 없습니다.\n",
        ),
    )
    _write_if_missing(
        paths.wiki_dir / "log.md",
        _wiki_page(
            title=f"{paths.topic} Research Log",
            topic=paths.topic,
            topic_slug=paths.topic_slug,
            page_type="log",
            body="## Activity\n- 토픽이 초기화되었습니다.\n",
        ),
    )
    return _paths_payload(paths)


def start_research_run(
    topic: str,
    *,
    run_id: Optional[str] = None,
    query: str = "",
    focus: Optional[List[str]] = None,
    planned_agents: Optional[List[str]] = None,
    notes: str = "",
    topic_slug: Optional[str] = None,
    entity_slug: Optional[str] = None,
    section_slug: Optional[str] = None,
    vault_dir: Optional[Path] = None,
) -> dict[str, str]:
    ensure_research_topic(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    paths = resolve_topic_paths(topic, topic_slug=topic_slug, entity_slug=entity_slug, vault_dir=vault_dir)
    effective_run_id = str(run_id or _timestamp_id()).strip()
    run_dir = paths.raw_topic_dir / effective_run_id
    (run_dir / "source_notes").mkdir(parents=True, exist_ok=True)
    (run_dir / "image_notes").mkdir(parents=True, exist_ok=True)
    (run_dir / "image_assets").mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    started_at = _now_iso()
    run_record = {
        "run_id": effective_run_id,
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "entity_slug": str(entity_slug or paths.raw_slug).strip(),
        "section_slug": str(section_slug or "").strip(),
        "raw_slug": paths.raw_slug,
        "query": query.strip(),
        "focus": _clean_list(focus),
        "planned_agents": _clean_list(planned_agents),
        "notes": notes.strip(),
        "stage": RUN_STAGES[0],
        "status": RUN_STATUSES[0],
        "completed_stages": [],
        "started_at": started_at,
        "updated_at": started_at,
        "run_path": _relative_to_root(run_dir, paths.research_root),
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(run_record, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "state.json").write_text(json.dumps(run_record, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_if_missing(run_dir / "source_manifest.jsonl", "")
    _write_if_missing(run_dir / "image_manifest.jsonl", "")
    _upsert_jsonl(paths.manifests_dir / "runs.jsonl", ["run_id"], run_record)
    (paths.manifests_dir / "latest_run.txt").write_text(effective_run_id + "\n", encoding="utf-8")
    _append_log_entry(
        paths,
        title=f"Run started: {effective_run_id}",
        bullets=[
            f"query: `{query.strip() or 'n/a'}`",
            f"focus: `{', '.join(_clean_list(focus)) or 'n/a'}`",
            f"planned_agents: `{', '.join(_clean_list(planned_agents)) or 'n/a'}`",
        ],
    )
    payload = _paths_payload(paths)
    payload.update(
        {
            "run_id": effective_run_id,
            "run_dir": str(run_dir),
            "run_manifest": str(run_dir / 'run_manifest.json'),
        }
    )
    return payload


def set_run_stage(
    topic: str,
    *,
    run_id: str,
    stage: str,
    status: str = "active",
    notes: str = "",
    mark_complete: bool = False,
    topic_slug: Optional[str] = None,
    entity_slug: Optional[str] = None,
    vault_dir: Optional[Path] = None,
) -> dict[str, Any]:
    paths = resolve_topic_paths(topic, topic_slug=topic_slug, entity_slug=entity_slug, vault_dir=vault_dir)
    run_dir = _existing_run_dir(paths, run_id)
    state_path = run_dir / "state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    else:
        state = {
            "run_id": run_id,
            "topic": paths.topic,
            "topic_slug": paths.topic_slug,
            "completed_stages": [],
            "started_at": _now_iso(),
        }

    normalized_stage = _normalize_run_stage(stage)
    normalized_status = _normalize_run_status(status)
    completed_stages = _clean_list(state.get("completed_stages") or [])
    if mark_complete and normalized_stage not in completed_stages:
        completed_stages.append(normalized_stage)

    state.update(
        {
            "run_id": run_id,
            "topic": paths.topic,
            "topic_slug": paths.topic_slug,
            "stage": normalized_stage,
            "status": normalized_status,
            "notes": str(notes).strip(),
            "completed_stages": completed_stages,
            "updated_at": _now_iso(),
        }
    )
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "run_manifest.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    _upsert_jsonl(paths.manifests_dir / "runs.jsonl", ["run_id"], state)
    _append_log_entry(
        paths,
        title=f"Run stage updated: {run_id}",
        bullets=[
            f"stage: `{normalized_stage}`",
            f"status: `{normalized_status}`",
            f"completed_stages: `{', '.join(completed_stages) or 'n/a'}`",
        ] + ([f"notes: {str(notes).strip()}"] if str(notes).strip() else []),
    )
    return state


def register_source_note(
    topic: str,
    *,
    run_id: str,
    title: str,
    source_url: str,
    note_markdown: str = "",
    source_kind: str = "web",
    source_id: Optional[str] = None,
    author: str = "",
    published_at: str = "",
    captured_at: str = "",
    language: str = "",
    license_name: str = "",
    quality_grade: str = "",
    summary: str = "",
    key_points: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    source_class: str = "",
    trust_tier: str = "",
    trust_score: str = "",
    domain: str = "",
    tier_reason: str = "",
    publisher_resolved: str = "",
    lane_id: str = "",
    discovery_confidence: str = "",
    discovered_via_query: str = "",
    discovery_stage: str = "",
    relevance_score: str = "",
    relevance_band: str = "",
    ranking_score: str = "",
    topic_slug: Optional[str] = None,
    vault_dir: Optional[Path] = None,
) -> dict[str, str]:
    paths = resolve_topic_paths(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    run_dir = _existing_run_dir(paths, run_id)
    effective_source_id = str(source_id or _stable_record_id("src", title, source_url, run_id)).strip()
    note_path = run_dir / "source_notes" / f"{effective_source_id}.md"
    record = {
        "source_id": effective_source_id,
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "run_id": run_id,
        "title": title.strip(),
        "source_url": source_url.strip(),
        "source_kind": source_kind.strip() or "web",
        "author": author.strip(),
        "published_at": published_at.strip(),
        "captured_at": captured_at.strip() or _now_iso(),
        "language": language.strip(),
        "license": license_name.strip(),
        "quality_grade": _normalize_quality_grade(quality_grade),
        "summary": summary.strip(),
        "key_points": _clean_list(key_points),
        "tags": sorted(set(_clean_list(tags) + ["raw-source"])),
        "source_class": source_class.strip(),
        "trust_tier": trust_tier.strip(),
        "trust_score": str(trust_score).strip(),
        "domain": domain.strip(),
        "tier_reason": tier_reason.strip(),
        "publisher_resolved": publisher_resolved.strip(),
        "lane_id": lane_id.strip(),
        "discovery_confidence": discovery_confidence.strip(),
        "discovered_via_query": discovered_via_query.strip(),
        "discovery_stage": discovery_stage.strip(),
        "relevance_score": str(relevance_score).strip(),
        "relevance_band": relevance_band.strip(),
        "ranking_score": str(ranking_score).strip(),
        "note_path": _relative_to_root(note_path, paths.research_root),
    }
    note_path.write_text(_source_note_markdown(record, note_markdown=note_markdown), encoding="utf-8")
    _upsert_jsonl(run_dir / "source_manifest.jsonl", ["source_id"], record)
    _upsert_jsonl(paths.manifests_dir / "sources.jsonl", ["source_id"], record)
    _append_log_entry(
        paths,
        title=f"Source registered: {record['title']}",
        bullets=[
            f"source_id: `{effective_source_id}`",
            f"source_kind: `{record['source_kind']}`",
            f"quality_grade: `{record['quality_grade'] or 'n/a'}`",
            f"source_class: `{record['source_class'] or 'n/a'}`",
            f"trust_tier: `{record['trust_tier'] or 'n/a'}`",
            f"url: {record['source_url']}",
        ],
    )
    return {
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "run_id": run_id,
        "source_id": effective_source_id,
        "note_path": str(note_path),
    }


def register_image_note(
    topic: str,
    *,
    run_id: str,
    title: str,
    source_url: str,
    caption: str,
    note_markdown: str = "",
    image_id: Optional[str] = None,
    asset_url: str = "",
    asset_file_path: str = "",
    creator: str = "",
    creator_url: str = "",
    license_name: str = "",
    license_url: str = "",
    attribution_text: str = "",
    copyright_notice: str = "",
    mime_type: str = "",
    relevance: str = "",
    linked_claim_ids: Optional[List[str]] = None,
    linked_pages: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    topic_slug: Optional[str] = None,
    vault_dir: Optional[Path] = None,
) -> dict[str, str]:
    paths = resolve_topic_paths(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    run_dir = _existing_run_dir(paths, run_id)
    effective_image_id = str(image_id or _stable_record_id("img", title, source_url, caption, run_id)).strip()
    note_path = run_dir / "image_notes" / f"{effective_image_id}.md"
    asset_details = _persist_image_asset(
        research_root=paths.research_root,
        run_dir=run_dir,
        image_id=effective_image_id,
        asset_url=asset_url.strip(),
        asset_file_path=asset_file_path.strip(),
        mime_type=mime_type.strip(),
    )
    record = {
        "image_id": effective_image_id,
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "run_id": run_id,
        "title": title.strip(),
        "source_url": source_url.strip(),
        "asset_url": asset_url.strip(),
        "caption": caption.strip(),
        "creator": creator.strip(),
        "creator_url": creator_url.strip(),
        "license": license_name.strip(),
        "license_url": license_url.strip(),
        "attribution_text": attribution_text.strip(),
        "copyright_notice": copyright_notice.strip(),
        "local_asset_path": asset_details["local_asset_path"],
        "asset_sha256": asset_details["asset_sha256"],
        "mime_type": asset_details["mime_type"],
        "asset_status": asset_details["asset_status"],
        "asset_error": asset_details["asset_error"],
        "relevance": relevance.strip(),
        "linked_claim_ids": _clean_list(linked_claim_ids),
        "linked_pages": _clean_list(linked_pages),
        "tags": sorted(set(_clean_list(tags) + ["image-source"])),
        "captured_at": _now_iso(),
        "note_path": _relative_to_root(note_path, paths.research_root),
    }
    note_path.write_text(_image_note_markdown(record, note_markdown=note_markdown), encoding="utf-8")
    _upsert_jsonl(run_dir / "image_manifest.jsonl", ["image_id"], record)
    _upsert_jsonl(paths.manifests_dir / "images.jsonl", ["image_id"], record)
    _upsert_markdown_section(
        paths.wiki_dir / "images.md",
        f"## {record['title']} ({effective_image_id})",
        [
            f"- caption: {record['caption'] or 'n/a'}",
            f"- source_url: {record['source_url'] or 'n/a'}",
            f"- asset_url: {record['asset_url'] or 'n/a'}",
            f"- local_asset_path: `{record['local_asset_path'] or 'n/a'}`",
            f"- asset_status: `{record['asset_status'] or 'n/a'}`",
            f"- mime_type: `{record['mime_type'] or 'n/a'}`",
            f"- creator: `{record['creator'] or 'n/a'}`",
            f"- creator_url: {record['creator_url'] or 'n/a'}",
            f"- license: `{record['license'] or 'n/a'}`",
            f"- license_url: {record['license_url'] or 'n/a'}",
            f"- attribution_text: {record['attribution_text'] or 'n/a'}",
            f"- copyright_notice: {record['copyright_notice'] or 'n/a'}",
            f"- relevance: `{record['relevance'] or 'n/a'}`",
            f"- linked_claim_ids: `{', '.join(record['linked_claim_ids']) or 'n/a'}`",
            f"- linked_pages: `{', '.join(record['linked_pages']) or 'n/a'}`",
            f"- note_path: `{record['note_path']}`",
        ],
    )
    _append_log_entry(
        paths,
        title=f"Image registered: {record['title']}",
        bullets=[
            f"image_id: `{effective_image_id}`",
            f"source_url: {record['source_url']}",
            f"asset_status: `{record['asset_status']}`",
            f"local_asset_path: `{record['local_asset_path'] or 'n/a'}`",
            f"linked_claim_ids: `{', '.join(record['linked_claim_ids']) or 'n/a'}`",
        ],
    )
    return {
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "run_id": run_id,
        "image_id": effective_image_id,
        "note_path": str(note_path),
        "local_asset_path": record["local_asset_path"],
        "asset_status": record["asset_status"],
    }


def ingest_packet(
    topic: str,
    *,
    run_id: str,
    packet_path: Path,
    topic_slug: Optional[str] = None,
    vault_dir: Optional[Path] = None,
    refresh_after_ingest: bool = False,
) -> dict[str, Any]:
    paths = resolve_topic_paths(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    run_dir = _existing_run_dir(paths, run_id)
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet_id = str(packet.get("packet_id") or packet_path.stem).strip() or f"packet-{_timestamp_id()}"
    packet_record_path = run_dir / "artifacts" / "packets" / f"{_safe_slug(packet_id)}.json"
    packet_record_path.parent.mkdir(parents=True, exist_ok=True)
    packet_record_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")

    source_key_to_id: dict[str, str] = {}
    claim_key_to_id: dict[str, str] = {}
    source_ids: list[str] = []
    claim_ids: list[str] = []
    image_ids: list[str] = []
    question_ids: list[str] = []

    for source in packet.get("sources") or []:
        source_key = str(source.get("source_key") or source.get("title") or source.get("source_url") or "").strip()
        result = register_source_note(
            topic,
            run_id=run_id,
            title=str(source.get("title") or "").strip(),
            source_url=str(source.get("source_url") or "").strip(),
            note_markdown=str(source.get("note_markdown") or source.get("body") or "").strip(),
            source_kind=str(source.get("source_kind") or "web").strip(),
            source_id=_optional_text(str(source.get("source_id") or "")),
            author=str(source.get("author") or "").strip(),
            published_at=str(source.get("published_at") or "").strip(),
            captured_at=str(source.get("captured_at") or "").strip(),
            language=str(source.get("language") or "").strip(),
            license_name=str(source.get("license_name") or source.get("license") or "").strip(),
            quality_grade=str(source.get("quality_grade") or "").strip(),
            summary=str(source.get("summary") or "").strip(),
            key_points=_clean_list(source.get("key_points") or []),
            tags=_clean_list(source.get("tags") or []),
            source_class=str(source.get("source_class") or "").strip(),
            trust_tier=str(source.get("trust_tier") or "").strip(),
            trust_score=str(source.get("trust_score") or "").strip(),
            domain=str(source.get("domain") or "").strip(),
            tier_reason=str(source.get("tier_reason") or "").strip(),
            publisher_resolved=str(source.get("publisher_resolved") or "").strip(),
            lane_id=str(source.get("lane_id") or "").strip(),
            discovery_confidence=str(source.get("discovery_confidence") or source.get("confidence") or "").strip(),
            discovered_via_query=str(source.get("discovered_via_query") or source.get("query") or "").strip(),
            discovery_stage=str(source.get("discovery_stage") or "").strip(),
            relevance_score=str(source.get("relevance_score") or "").strip(),
            relevance_band=str(source.get("relevance_band") or "").strip(),
            ranking_score=str(source.get("ranking_score") or "").strip(),
            topic_slug=topic_slug,
            vault_dir=vault_dir,
        )
        if source_key:
            source_key_to_id[source_key] = result["source_id"]
        source_ids.append(result["source_id"])

    for claim in packet.get("claims") or []:
        claim_key = str(claim.get("claim_key") or claim.get("claim") or "").strip()
        mapped_source_ids = _merge_reference_ids(
            explicit_ids=_clean_list(claim.get("source_ids") or []),
            reference_keys=_clean_list(claim.get("source_keys") or []),
            key_map=source_key_to_id,
        )
        result = append_claim(
            topic,
            claim=str(claim.get("claim") or "").strip(),
            source_ids=mapped_source_ids,
            run_id=run_id,
            claim_id=_optional_text(str(claim.get("claim_id") or "")),
            kind=str(claim.get("kind") or "fact").strip(),
            confidence=str(claim.get("confidence") or "working").strip(),
            evidence=str(claim.get("evidence") or "").strip(),
            counterpoints=_clean_list(claim.get("counterpoints") or []),
            linked_pages=_clean_list(claim.get("linked_pages") or []),
            status=str(claim.get("status") or "active").strip(),
            topic_slug=topic_slug,
            vault_dir=vault_dir,
        )
        if claim_key:
            claim_key_to_id[claim_key] = result["claim_id"]
        claim_ids.append(result["claim_id"])

    for image in packet.get("images") or []:
        mapped_claim_ids = _merge_reference_ids(
            explicit_ids=_clean_list(image.get("linked_claim_ids") or []),
            reference_keys=_clean_list(image.get("linked_claim_keys") or []),
            key_map=claim_key_to_id,
        )
        result = register_image_note(
            topic,
            run_id=run_id,
            title=str(image.get("title") or "").strip(),
            source_url=str(image.get("source_url") or "").strip(),
            caption=str(image.get("caption") or "").strip(),
            note_markdown=str(image.get("note_markdown") or image.get("body") or "").strip(),
            image_id=_optional_text(str(image.get("image_id") or "")),
            asset_url=str(image.get("asset_url") or "").strip(),
            asset_file_path=_resolve_asset_file_path(
                packet_path=packet_path,
                raw_value=str(image.get("asset_file_path") or "").strip(),
            ),
            creator=str(image.get("creator") or "").strip(),
            creator_url=str(image.get("creator_url") or "").strip(),
            license_name=str(image.get("license_name") or image.get("license") or "").strip(),
            license_url=str(image.get("license_url") or "").strip(),
            attribution_text=str(image.get("attribution_text") or "").strip(),
            copyright_notice=str(image.get("copyright_notice") or "").strip(),
            mime_type=str(image.get("mime_type") or "").strip(),
            relevance=str(image.get("relevance") or "").strip(),
            linked_claim_ids=mapped_claim_ids,
            linked_pages=_clean_list(image.get("linked_pages") or []),
            tags=_clean_list(image.get("tags") or []),
            topic_slug=topic_slug,
            vault_dir=vault_dir,
        )
        image_ids.append(result["image_id"])

    for question in packet.get("open_questions") or []:
        mapped_claim_ids = _merge_reference_ids(
            explicit_ids=_clean_list(question.get("related_claim_ids") or []),
            reference_keys=_clean_list(question.get("related_claim_keys") or []),
            key_map=claim_key_to_id,
        )
        result = append_open_question(
            topic,
            question=str(question.get("question") or "").strip(),
            question_id=_optional_text(str(question.get("question_id") or "")),
            priority=str(question.get("priority") or "medium").strip(),
            owner=str(question.get("owner") or "").strip(),
            context=str(question.get("context") or "").strip(),
            related_claim_ids=mapped_claim_ids,
            topic_slug=topic_slug,
            vault_dir=vault_dir,
        )
        question_ids.append(result["question_id"])

    _append_log_entry(
        paths,
        title=f"Packet ingested: {packet_id}",
        bullets=[
            f"packet_file: `{packet_path}`",
            f"sources_added: `{len(source_ids)}`",
            f"claims_added: `{len(claim_ids)}`",
            f"images_added: `{len(image_ids)}`",
            f"questions_added: `{len(question_ids)}`",
        ],
    )

    payload: dict[str, Any] = {
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "run_id": run_id,
        "packet_id": packet_id,
        "packet_record_path": str(packet_record_path),
        "source_ids": source_ids,
        "claim_ids": claim_ids,
        "image_ids": image_ids,
        "question_ids": question_ids,
    }
    if refresh_after_ingest:
        payload["snapshot"] = refresh_topic_snapshot(
            topic,
            topic_slug=topic_slug,
            vault_dir=vault_dir,
        )
    return payload


def append_claim(
    topic: str,
    *,
    claim: str,
    source_ids: Optional[List[str]] = None,
    run_id: str = "",
    claim_id: Optional[str] = None,
    kind: str = "fact",
    confidence: str = "working",
    evidence: str = "",
    counterpoints: Optional[List[str]] = None,
    linked_pages: Optional[List[str]] = None,
    status: str = "active",
    topic_slug: Optional[str] = None,
    vault_dir: Optional[Path] = None,
) -> dict[str, str]:
    paths = resolve_topic_paths(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    ensure_research_topic(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    effective_claim_id = str(claim_id or _stable_record_id("claim", claim, run_id, ",".join(_clean_list(source_ids)))).strip()
    record = {
        "claim_id": effective_claim_id,
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "run_id": run_id.strip(),
        "claim": claim.strip(),
        "kind": kind.strip() or "fact",
        "confidence": confidence.strip() or "working",
        "evidence": evidence.strip(),
        "source_ids": _clean_list(source_ids),
        "counterpoints": _clean_list(counterpoints),
        "linked_pages": _clean_list(linked_pages),
        "status": status.strip() or "active",
        "created_at": _now_iso(),
    }
    _upsert_jsonl(paths.manifests_dir / "claims.jsonl", ["claim_id"], record)
    _upsert_markdown_section(
        paths.wiki_dir / "claims.md",
        f"## {effective_claim_id}",
        [
            f"- claim: {record['claim']}",
            f"- kind: `{record['kind']}`",
            f"- confidence: `{record['confidence']}`",
            f"- status: `{record['status']}`",
            f"- source_ids: `{', '.join(record['source_ids']) or 'n/a'}`",
            f"- linked_pages: `{', '.join(record['linked_pages']) or 'n/a'}`",
            f"- run_id: `{record['run_id'] or 'n/a'}`",
            f"- created_at: `{record['created_at']}`",
        ]
        + ([f"- evidence: {record['evidence']}"] if record["evidence"] else [])
        + [f"- counterpoint: {item}" for item in record["counterpoints"]],
    )
    _append_log_entry(
        paths,
        title=f"Claim appended: {effective_claim_id}",
        bullets=[
            f"claim: {record['claim']}",
            f"source_ids: `{', '.join(record['source_ids']) or 'n/a'}`",
            f"confidence: `{record['confidence']}`",
        ],
    )
    return {
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "claim_id": effective_claim_id,
        "claims_manifest": str(paths.manifests_dir / "claims.jsonl"),
    }


def append_open_question(
    topic: str,
    *,
    question: str,
    question_id: Optional[str] = None,
    priority: str = "medium",
    owner: str = "",
    context: str = "",
    related_claim_ids: Optional[List[str]] = None,
    topic_slug: Optional[str] = None,
    vault_dir: Optional[Path] = None,
) -> dict[str, str]:
    paths = resolve_topic_paths(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    ensure_research_topic(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    effective_question_id = str(question_id or _stable_record_id("q", question, priority, owner)).strip()
    record = {
        "question_id": effective_question_id,
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "question": question.strip(),
        "priority": priority.strip() or "medium",
        "owner": owner.strip(),
        "context": context.strip(),
        "related_claim_ids": _clean_list(related_claim_ids),
        "status": "open",
        "created_at": _now_iso(),
    }
    _upsert_jsonl(paths.manifests_dir / "open_questions.jsonl", ["question_id"], record)
    _upsert_markdown_section(
        paths.wiki_dir / "questions.md",
        f"## {effective_question_id}",
        [
            f"- question: {record['question']}",
            f"- priority: `{record['priority']}`",
            f"- owner: `{record['owner'] or 'n/a'}`",
            f"- related_claim_ids: `{', '.join(record['related_claim_ids']) or 'n/a'}`",
            f"- created_at: `{record['created_at']}`",
        ]
        + ([f"- context: {record['context']}"] if record["context"] else []),
    )
    _append_log_entry(
        paths,
        title=f"Open question appended: {effective_question_id}",
        bullets=[
            f"priority: `{record['priority']}`",
            f"question: {record['question']}",
        ],
    )
    return {
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "question_id": effective_question_id,
        "questions_manifest": str(paths.manifests_dir / "open_questions.jsonl"),
    }


def refresh_topic_snapshot(
    topic: str,
    *,
    topic_slug: Optional[str] = None,
    vault_dir: Optional[Path] = None,
) -> dict[str, Any]:
    paths = resolve_topic_paths(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    ensure_research_topic(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    sources = _load_jsonl(paths.manifests_dir / "sources.jsonl")
    images = _load_jsonl(paths.manifests_dir / "images.jsonl")
    claims = _load_jsonl(paths.manifests_dir / "claims.jsonl")
    questions = _load_jsonl(paths.manifests_dir / "open_questions.jsonl")
    runs = _load_jsonl(paths.manifests_dir / "runs.jsonl")
    latest_run = _latest_run_record(paths, runs)
    specialist_report = _build_specialist_report(
        paths,
        sources=sources,
        claims=claims,
        questions=questions,
        latest_run=latest_run,
    )
    counts = {
        "run_count": len(runs),
        "source_count": len(sources),
        "image_count": len(images),
        "claim_count": len(claims),
        "open_question_count": len(questions),
        "updated_at": _now_iso(),
        "latest_run_id": str(latest_run.get("run_id") or ""),
        "latest_run_stage": str(latest_run.get("stage") or ""),
        "latest_run_status": str(latest_run.get("status") or ""),
        "latest_run_completed_stages": _clean_list(latest_run.get("completed_stages") or []),
        "specialist_readiness": str(specialist_report.get("readiness") or "seed_only"),
    }
    snapshot = _topic_snapshot_markdown(
        paths,
        overview_body=_markdown_body(paths.wiki_dir / "overview.md"),
        sources=sources,
        images=images,
        claims=claims,
        questions=questions,
        counts=counts,
        specialist_report=specialist_report,
    )
    paths.topic_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    paths.topic_snapshot_path.write_text(snapshot, encoding="utf-8")
    paths.specialist_report_path.write_text(
        json.dumps(specialist_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    paths.executive_summary_path.write_text(
        _executive_summary_markdown(
            paths,
            specialist_report=specialist_report,
            claims=claims,
            questions=questions,
            sources=sources,
        ),
        encoding="utf-8",
    )
    (paths.wiki_dir / "index.md").write_text(
        _topic_index_markdown(paths, counts=counts, specialist_report=specialist_report),
        encoding="utf-8",
    )
    return {
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "snapshot_path": str(paths.topic_snapshot_path),
        "specialist_report_path": str(paths.specialist_report_path),
        "executive_summary_path": str(paths.executive_summary_path),
        **counts,
    }


def lint_research_topic(
    topic: str,
    *,
    topic_slug: Optional[str] = None,
    vault_dir: Optional[Path] = None,
) -> dict[str, Any]:
    paths = resolve_topic_paths(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    issues: list[dict[str, str]] = []
    required_dirs = [paths.raw_topic_dir, paths.manifests_dir, paths.wiki_dir]
    required_files = [
        paths.manifests_dir / "sources.jsonl",
        paths.manifests_dir / "images.jsonl",
        paths.manifests_dir / "claims.jsonl",
        paths.manifests_dir / "open_questions.jsonl",
        paths.manifests_dir / "runs.jsonl",
        paths.wiki_dir / "overview.md",
        paths.wiki_dir / "claims.md",
        paths.wiki_dir / "entities.md",
        paths.wiki_dir / "timeline.md",
        paths.wiki_dir / "images.md",
        paths.wiki_dir / "questions.md",
        paths.wiki_dir / "log.md",
    ]
    for directory in required_dirs:
        if not directory.exists():
            issues.append(_issue("error", f"Missing directory: {directory}"))
    for file_path in required_files:
        if not file_path.exists():
            issues.append(_issue("error", f"Missing file: {file_path}"))
    if any(issue["level"] == "error" for issue in issues):
        return _lint_payload(paths, issues)

    sources = _load_jsonl(paths.manifests_dir / "sources.jsonl")
    images = _load_jsonl(paths.manifests_dir / "images.jsonl")
    claims = _load_jsonl(paths.manifests_dir / "claims.jsonl")
    questions = _load_jsonl(paths.manifests_dir / "open_questions.jsonl")
    runs = _load_jsonl(paths.manifests_dir / "runs.jsonl")

    if not sources:
        issues.append(_issue("warning", "No source records registered yet."))
    if not claims:
        issues.append(_issue("warning", "No claims registered yet."))
    if not paths.topic_snapshot_path.exists():
        issues.append(_issue("warning", "Topic snapshot has not been refreshed yet."))
    if not paths.specialist_report_path.exists():
        issues.append(_issue("warning", "Specialist report has not been generated yet. Run `refresh-topic` or `finalize-session`."))
    if not paths.executive_summary_path.exists():
        issues.append(_issue("warning", "Executive summary has not been generated yet. Run `refresh-topic` or `finalize-session`."))

    source_by_id = {str(item.get("source_id")): item for item in sources if item.get("source_id")}
    source_ids = set(source_by_id)
    claim_ids = {str(item.get("claim_id")) for item in claims if item.get("claim_id")}
    for source in sources:
        note_path = paths.research_root / str(source.get("note_path") or "")
        if not note_path.exists():
            issues.append(_issue("error", f"Missing source note for source_id `{source.get('source_id')}`: {note_path}"))
        grade = str(source.get("quality_grade") or "").strip().upper()
        if not grade:
            issues.append(_issue("warning", f"Source `{source.get('source_id')}` is missing a quality grade."))
        elif grade not in SOURCE_QUALITY_GRADES:
            issues.append(_issue("error", f"Source `{source.get('source_id')}` has unsupported quality grade `{grade}`."))
    for image in images:
        note_path = paths.research_root / str(image.get("note_path") or "")
        if not note_path.exists():
            issues.append(_issue("error", f"Missing image note for image_id `{image.get('image_id')}`: {note_path}"))
        local_asset_path = str(image.get("local_asset_path") or "").strip()
        if local_asset_path:
            asset_path = paths.research_root / local_asset_path
            if not asset_path.exists():
                issues.append(_issue("error", f"Missing stored image asset for image_id `{image.get('image_id')}`: {asset_path}"))
            if not (
                str(image.get("creator") or "").strip()
                or str(image.get("attribution_text") or "").strip()
                or str(image.get("copyright_notice") or "").strip()
            ):
                issues.append(_issue("warning", f"Stored image `{image.get('image_id')}` is missing creator or attribution metadata."))
            if not (str(image.get("license") or "").strip() or str(image.get("license_url") or "").strip()):
                issues.append(_issue("warning", f"Stored image `{image.get('image_id')}` is missing license metadata."))
        if str(image.get("asset_status") or "").strip() == "failed":
            issues.append(
                _issue(
                    "warning",
                    f"Image `{image.get('image_id')}` asset persistence failed: {str(image.get('asset_error') or 'unknown error')}",
                )
            )
        for linked_claim_id in image.get("linked_claim_ids") or []:
            if str(linked_claim_id) not in claim_ids:
                issues.append(_issue("error", f"Image `{image.get('image_id')}` references unknown claim `{linked_claim_id}`."))
        if not (image.get("linked_claim_ids") or []) and not (image.get("linked_pages") or []):
            issues.append(_issue("warning", f"Image `{image.get('image_id')}` is not linked to any claim or page."))
    for claim in claims:
        claim_source_ids = [str(source_id) for source_id in claim.get("source_ids") or []]
        if not claim_source_ids:
            issues.append(_issue("error", f"Claim `{claim.get('claim_id')}` has no source references."))
        missing = [source_id for source_id in claim.get("source_ids") or [] if str(source_id) not in source_ids]
        if missing:
            issues.append(_issue("error", f"Claim `{claim.get('claim_id')}` references missing sources: {', '.join(missing)}"))
        confidence = str(claim.get("confidence") or "").strip().lower()
        linked_sources = [source_by_id[source_id] for source_id in claim_source_ids if source_id in source_by_id]
        strong_sources = [
            source for source in linked_sources
            if str(source.get("quality_grade") or "").strip().upper() in {"A", "B"}
        ]
        if confidence == "high" and len(claim_source_ids) < 2:
            issues.append(_issue("warning", f"High-confidence claim `{claim.get('claim_id')}` has fewer than 2 sources for cross-verification."))
        if confidence == "high" and not strong_sources:
            issues.append(_issue("warning", f"High-confidence claim `{claim.get('claim_id')}` is not backed by any A/B quality sources."))
    for question in questions:
        missing = [str(claim_id) for claim_id in question.get("related_claim_ids") or [] if str(claim_id) not in claim_ids]
        if missing:
            issues.append(_issue("error", f"Question `{question.get('question_id')}` references missing claims: {', '.join(missing)}"))

    specialist_report = _build_specialist_report(
        paths,
        sources=sources,
        claims=claims,
        questions=questions,
        latest_run=_latest_run_record(paths, runs),
    )
    readiness = str(specialist_report.get("readiness") or "seed_only")
    if readiness == "seed_only":
        issues.append(_issue("warning", "Specialist readiness is still `seed_only`; strengthen the claim set before packaging."))
    if int(specialist_report.get("metrics", {}).get("high_priority_open_question_count") or 0) > 0:
        issues.append(_issue("warning", "High-priority open questions remain unresolved."))
    if int(specialist_report.get("metrics", {}).get("unsupported_claim_count") or 0) > 0:
        issues.append(_issue("warning", "Some claims are not backed by durable registered sources."))

    latest_run_path = paths.manifests_dir / "latest_run.txt"
    if latest_run_path.exists():
        latest_run_id = latest_run_path.read_text(encoding="utf-8").strip()
        if latest_run_id:
            candidate_dirs = _candidate_raw_dirs(paths, latest_run_id)
            if not any(path.exists() for path in candidate_dirs):
                issues.append(_issue("error", f"latest_run.txt points to missing run directory `{latest_run_id}`."))
        elif latest_run_id:
            latest_run_state = _load_run_state(paths, latest_run_id)
            if latest_run_state:
                latest_stage = str(latest_run_state.get("stage") or "").strip()
                latest_status = str(latest_run_state.get("status") or "").strip()
                if latest_stage and latest_stage not in RUN_STAGES:
                    issues.append(_issue("error", f"Latest run `{latest_run_id}` has unsupported stage `{latest_stage}`."))
                if latest_status and latest_status not in RUN_STATUSES:
                    issues.append(_issue("error", f"Latest run `{latest_run_id}` has unsupported status `{latest_status}`."))
                if latest_status != "completed":
                    issues.append(_issue("warning", f"Latest run `{latest_run_id}` is not completed yet. Current stage: `{latest_stage or 'n/a'}`."))
                if latest_status == "completed" and latest_stage != "packaging":
                    issues.append(_issue("warning", f"Latest run `{latest_run_id}` is completed but final stage is `{latest_stage or 'n/a'}` instead of `packaging`."))
    if not runs:
        issues.append(_issue("warning", "No run history registered yet."))

    return _lint_payload(paths, issues)


def _paths_payload(paths: ResearchTopicPaths) -> dict[str, str]:
    return {
        "research_root": str(paths.research_root),
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "raw_slug": paths.raw_slug,
        "raw_topic_dir": str(paths.raw_topic_dir),
        "manifests_dir": str(paths.manifests_dir),
        "wiki_dir": str(paths.wiki_dir),
        "topic_snapshot_path": str(paths.topic_snapshot_path),
        "specialist_report_path": str(paths.specialist_report_path),
        "executive_summary_path": str(paths.executive_summary_path),
    }


def _source_note_markdown(record: dict[str, Any], *, note_markdown: str) -> str:
    return "\n".join(
        [
            _frontmatter_block(
                {
                    "doc_type": "raw-source",
                    "topic": record["topic"],
                    "topic_slug": record["topic_slug"],
                    "run_id": record["run_id"],
                    "source_id": record["source_id"],
                    "source_kind": record["source_kind"],
                    "source_url": record["source_url"],
                    "author": record["author"],
                    "published_at": record["published_at"],
                    "captured_at": record["captured_at"],
                    "language": record["language"],
                    "license": record["license"],
                    "quality_grade": record["quality_grade"],
                    "source_class": record["source_class"],
                    "trust_tier": record["trust_tier"],
                    "trust_score": record["trust_score"],
                    "domain": record["domain"],
                    "tier_reason": record["tier_reason"],
                    "publisher_resolved": record["publisher_resolved"],
                    "lane_id": record["lane_id"],
                    "discovery_confidence": record["discovery_confidence"],
                    "discovered_via_query": record["discovered_via_query"],
                    "discovery_stage": record["discovery_stage"],
                    "relevance_score": record["relevance_score"],
                    "relevance_band": record["relevance_band"],
                    "ranking_score": record["ranking_score"],
                    "tags": record["tags"],
                }
            ),
            "",
            f"# {record['title']}",
            "",
            "## Source Quality",
            record["quality_grade"] or "- none",
            "",
            "## Summary",
            record["summary"] or "- none",
            "",
            "## Key Points",
            *[f"- {item}" for item in (record["key_points"] or ["none recorded"])],
            "",
            "## Discovery Metadata",
            f"- source_class: `{record['source_class'] or 'n/a'}`",
            f"- trust_tier: `{record['trust_tier'] or 'n/a'}`",
            f"- trust_score: `{record['trust_score'] or 'n/a'}`",
            f"- domain: `{record['domain'] or 'n/a'}`",
            f"- tier_reason: {record['tier_reason'] or 'n/a'}",
            f"- publisher_resolved: `{record['publisher_resolved'] or 'n/a'}`",
            f"- lane_id: `{record['lane_id'] or 'n/a'}`",
            f"- discovery_confidence: `{record['discovery_confidence'] or 'n/a'}`",
            f"- discovered_via_query: {record['discovered_via_query'] or 'n/a'}",
            f"- discovery_stage: `{record['discovery_stage'] or 'n/a'}`",
            f"- relevance_score: `{record['relevance_score'] or 'n/a'}`",
            f"- relevance_band: `{record['relevance_band'] or 'n/a'}`",
            f"- ranking_score: `{record['ranking_score'] or 'n/a'}`",
            "",
            "## Raw Notes",
            note_markdown.strip() or "_No raw note body captured._",
            "",
        ]
    )


def _image_note_markdown(record: dict[str, Any], *, note_markdown: str) -> str:
    return "\n".join(
        [
            _frontmatter_block(
                {
                    "doc_type": "image-source",
                    "topic": record["topic"],
                    "topic_slug": record["topic_slug"],
                    "run_id": record["run_id"],
                    "image_id": record["image_id"],
                    "source_url": record["source_url"],
                    "asset_url": record["asset_url"],
                    "local_asset_path": record["local_asset_path"],
                    "asset_sha256": record["asset_sha256"],
                    "mime_type": record["mime_type"],
                    "asset_status": record["asset_status"],
                    "asset_error": record["asset_error"],
                    "creator": record["creator"],
                    "creator_url": record["creator_url"],
                    "license": record["license"],
                    "license_url": record["license_url"],
                    "attribution_text": record["attribution_text"],
                    "copyright_notice": record["copyright_notice"],
                    "captured_at": record["captured_at"],
                    "linked_claim_ids": record["linked_claim_ids"],
                    "linked_pages": record["linked_pages"],
                    "tags": record["tags"],
                }
            ),
            "",
            f"# {record['title']}",
            "",
            "## Caption",
            record["caption"] or "- none",
            "",
            "## Stored Asset",
            f"- asset_url: {record['asset_url'] or 'n/a'}",
            f"- local_asset_path: `{record['local_asset_path'] or 'n/a'}`",
            f"- asset_status: `{record['asset_status'] or 'n/a'}`",
            f"- mime_type: `{record['mime_type'] or 'n/a'}`",
            f"- asset_sha256: `{record['asset_sha256'] or 'n/a'}`",
            f"- asset_error: {record['asset_error'] or 'n/a'}",
            "",
            "## Rights",
            f"- creator: `{record['creator'] or 'n/a'}`",
            f"- creator_url: {record['creator_url'] or 'n/a'}",
            f"- license: `{record['license'] or 'n/a'}`",
            f"- license_url: {record['license_url'] or 'n/a'}",
            f"- attribution_text: {record['attribution_text'] or 'n/a'}",
            f"- copyright_notice: {record['copyright_notice'] or 'n/a'}",
            "",
            "## Relevance",
            record["relevance"] or "- none",
            "",
            "## Notes",
            note_markdown.strip() or "_No image note body captured._",
            "",
        ]
    )


def _topic_snapshot_markdown(
    paths: ResearchTopicPaths,
    *,
    overview_body: str,
    sources: list[dict[str, Any]],
    images: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    counts: dict[str, Any],
    specialist_report: dict[str, Any],
) -> str:
    lines = [
        _frontmatter_block(
            {
                "doc_type": "topic-research-snapshot",
                "topic": paths.topic,
                "topic_slug": paths.topic_slug,
                "updated_at": counts["updated_at"],
                "claim_count": counts["claim_count"],
                "source_count": counts["source_count"],
                "image_count": counts["image_count"],
                "open_question_count": counts["open_question_count"],
                "specialist_readiness": specialist_report.get("readiness") or "seed_only",
                "tags": ["research", "llm-wiki"],
            }
        ),
        "",
        f"# {paths.topic}",
        "",
        "## Snapshot",
        f"- topic_slug: `{paths.topic_slug}`",
        f"- run_count: `{counts['run_count']}`",
        f"- latest_run_id: `{counts['latest_run_id'] or 'n/a'}`",
        f"- latest_run_stage: `{counts['latest_run_stage'] or 'n/a'}`",
        f"- latest_run_status: `{counts['latest_run_status'] or 'n/a'}`",
        f"- source_count: `{counts['source_count']}`",
        f"- image_count: `{counts['image_count']}`",
        f"- claim_count: `{counts['claim_count']}`",
        f"- open_question_count: `{counts['open_question_count']}`",
        f"- specialist_readiness: `{specialist_report.get('readiness') or 'seed_only'}`",
        f"- updated_at: `{counts['updated_at']}`",
        f"- completed_stages: `{', '.join(counts['latest_run_completed_stages']) or 'n/a'}`",
        f"- specialist_report: [json](./{paths.specialist_report_path.name})",
        f"- executive_summary: [md](./{paths.executive_summary_path.name})",
        "",
        "## Overview",
        overview_body.strip() or "- overview.md에 아직 정리된 본문이 없습니다.",
        "",
        "## Specialist Assessment",
        f"- readiness: `{specialist_report.get('readiness') or 'seed_only'}`",
        f"- target_claim_floor: `{specialist_report.get('target_claim_floor') or 0}`",
    ]
    for item in specialist_report.get("strengths") or []:
        lines.append(f"- strength: {item}")
    for item in specialist_report.get("gaps") or []:
        lines.append(f"- gap: {item}")
    lines.extend(
        [
            "",
        "## Top Claims",
        ]
    )
    if claims:
        for claim in claims[:10]:
            lines.append(f"- `{claim.get('claim_id', 'unknown')}` [{claim.get('confidence', 'n/a')}] {claim.get('claim', '').strip()}")
    else:
        lines.append("- 아직 기록된 claim이 없습니다.")
    lines.extend(["", "## Sources"])
    if sources:
        for source in sources[:10]:
            lines.append(f"- `{source.get('source_id', 'unknown')}` {source.get('title', '').strip()} · {source.get('source_kind', 'n/a')} · {source.get('source_url', '').strip()}")
    else:
        lines.append("- 아직 등록된 source가 없습니다.")
    lines.extend(["", "## Images"])
    if images:
        for image in images[:10]:
            lines.append(f"- `{image.get('image_id', 'unknown')}` {image.get('title', '').strip()} · {image.get('source_url', '').strip()}")
    else:
        lines.append("- 아직 등록된 이미지가 없습니다.")
    lines.extend(["", "## Open Questions"])
    if questions:
        for question in questions[:10]:
            lines.append(f"- `{question.get('question_id', 'unknown')}` [{question.get('priority', 'n/a')}] {question.get('question', '').strip()}")
    else:
        lines.append("- 아직 열린 질문이 없습니다.")
    lines.extend(
        [
            "",
            "## Canonical Wiki",
            f"- [index](../wiki/{paths.topic_slug}/index.md)",
            f"- [overview](../wiki/{paths.topic_slug}/overview.md)",
            f"- [claims](../wiki/{paths.topic_slug}/claims.md)",
            f"- [entities](../wiki/{paths.topic_slug}/entities.md)",
            f"- [timeline](../wiki/{paths.topic_slug}/timeline.md)",
            f"- [images](../wiki/{paths.topic_slug}/images.md)",
            f"- [questions](../wiki/{paths.topic_slug}/questions.md)",
            f"- [log](../wiki/{paths.topic_slug}/log.md)",
            f"- [specialist_report](./{paths.specialist_report_path.name})",
            f"- [executive_summary](./{paths.executive_summary_path.name})",
            "",
        ]
    )
    return "\n".join(lines)


def _wiki_page(*, title: str, topic: str, topic_slug: str, page_type: str, body: str) -> str:
    return "\n".join(
        [
            _frontmatter_block(
                {
                    "doc_type": "wiki-page",
                    "topic": topic,
                    "topic_slug": topic_slug,
                    "page_type": page_type,
                    "updated_at": _now_iso(),
                    "tags": ["wiki"],
                }
            ),
            "",
            f"# {title}",
            "",
            body.rstrip(),
            "",
        ]
    )


def _topic_index_markdown(
    paths: ResearchTopicPaths,
    counts: Optional[dict[str, Any]],
    specialist_report: Optional[dict[str, Any]] = None,
) -> str:
    lines = [
        f"# {paths.topic}",
        "",
        "## Canonical Pages",
        "- [overview](./overview.md)",
        "- [claims](./claims.md)",
        "- [entities](./entities.md)",
        "- [timeline](./timeline.md)",
        "- [images](./images.md)",
        "- [questions](./questions.md)",
        "- [log](./log.md)",
        f"- [specialist_report](../../topics/{paths.specialist_report_path.name})",
        f"- [executive_summary](../../topics/{paths.executive_summary_path.name})",
    ]
    if counts:
        lines.extend(
            [
                "",
                "## Coverage",
                f"- run_count: `{counts['run_count']}`",
                f"- latest_run_id: `{counts['latest_run_id'] or 'n/a'}`",
                f"- latest_run_stage: `{counts['latest_run_stage'] or 'n/a'}`",
                f"- latest_run_status: `{counts['latest_run_status'] or 'n/a'}`",
                f"- source_count: `{counts['source_count']}`",
                f"- image_count: `{counts['image_count']}`",
                f"- claim_count: `{counts['claim_count']}`",
                f"- open_question_count: `{counts['open_question_count']}`",
                f"- specialist_readiness: `{counts.get('specialist_readiness') or 'seed_only'}`",
                f"- updated_at: `{counts['updated_at']}`",
            ]
        )
    if specialist_report:
        lines.extend(
            [
                "",
                "## Specialist Assessment",
                f"- readiness: `{specialist_report.get('readiness') or 'seed_only'}`",
                f"- target_claim_floor: `{specialist_report.get('target_claim_floor') or 0}`",
            ]
        )
        for item in specialist_report.get("strengths") or []:
            lines.append(f"- strength: {item}")
        for item in specialist_report.get("gaps") or []:
            lines.append(f"- gap: {item}")
    lines.append("")
    return "\n".join(lines)


def _build_specialist_report(
    paths: ResearchTopicPaths,
    *,
    sources: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    latest_run: dict[str, Any],
) -> dict[str, Any]:
    source_by_id = {
        str(item.get("source_id") or "").strip(): item
        for item in sources
        if str(item.get("source_id") or "").strip()
    }
    active_claims = [
        item for item in claims
        if str(item.get("status") or "active").strip() != "discarded"
    ]
    open_questions = [
        item for item in questions
        if str(item.get("status") or "open").strip() != "resolved"
    ]
    high_priority_open_questions = [
        item for item in open_questions
        if str(item.get("priority") or "medium").strip().lower() in {"high", "critical"}
    ]
    high_grade_sources = [
        item for item in sources
        if str(item.get("quality_grade") or "").strip().upper() in {"A", "B"}
    ]
    graded_sources = [
        item for item in sources
        if str(item.get("quality_grade") or "").strip().upper() in SOURCE_QUALITY_GRADES
    ]
    supported_claims = []
    unsupported_claims = []
    high_confidence_claims = []
    cross_verified_high_confidence_claims = []

    for claim in active_claims:
        claim_source_ids = [str(source_id).strip() for source_id in claim.get("source_ids") or [] if str(source_id).strip()]
        linked_sources = [source_by_id[source_id] for source_id in claim_source_ids if source_id in source_by_id]
        if linked_sources:
            supported_claims.append(claim)
        else:
            unsupported_claims.append(claim)
        confidence = str(claim.get("confidence") or "").strip().lower()
        if confidence == "high":
            high_confidence_claims.append(claim)
            if len(linked_sources) >= 2 and any(
                str(source.get("quality_grade") or "").strip().upper() in {"A", "B"}
                for source in linked_sources
            ):
                cross_verified_high_confidence_claims.append(claim)

    target_claim_floor = max(5, min(12, max(5, len(high_grade_sources) + 2)))
    usable_claim_floor = max(2, target_claim_floor // 3)
    readiness = "seed_only"
    if (
        len(active_claims) >= target_claim_floor
        and len(high_grade_sources) >= 3
        and (
            not high_confidence_claims
            or len(cross_verified_high_confidence_claims) >= max(1, len(high_confidence_claims) // 2)
        )
        and not high_priority_open_questions
    ):
        readiness = "strong"
    elif (
        len(active_claims) >= usable_claim_floor
        and len(high_grade_sources) >= 2
        and len(supported_claims) == len(active_claims)
    ):
        readiness = "usable"

    source_quality_distribution = {
        grade: sum(1 for item in sources if str(item.get("quality_grade") or "").strip().upper() == grade)
        for grade in SOURCE_QUALITY_GRADES
    }
    strengths: list[str] = []
    if high_grade_sources:
        strengths.append(f"A/B grade sources are present ({len(high_grade_sources)}).")
    if active_claims and len(supported_claims) == len(active_claims):
        strengths.append("Every active claim is linked to at least one durable source note.")
    if cross_verified_high_confidence_claims:
        strengths.append(
            f"{len(cross_verified_high_confidence_claims)} high-confidence claim(s) are cross-verified by multiple sources."
        )
    if not open_questions:
        strengths.append("No unresolved open questions remain in the current vault state.")

    gaps: list[str] = []
    if len(active_claims) < target_claim_floor:
        gaps.append(f"Claim count is below the strong target floor ({target_claim_floor}).")
    if len(high_grade_sources) < 2:
        gaps.append("At least two A/B grade sources are still needed for durable handoff quality.")
    if unsupported_claims:
        gaps.append("Some claims still lack durable linked source notes.")
    if high_priority_open_questions:
        gaps.append("High-priority open questions remain unresolved.")
    if high_confidence_claims and not cross_verified_high_confidence_claims:
        gaps.append("High-confidence claims are not yet cross-verified across multiple sources.")

    return {
        "version": "researchagent-specialist-v1",
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "readiness": readiness,
        "target_claim_floor": target_claim_floor,
        "latest_run_id": str(latest_run.get("run_id") or ""),
        "latest_run_stage": str(latest_run.get("stage") or ""),
        "latest_run_status": str(latest_run.get("status") or ""),
        "metrics": {
            "source_count": len(sources),
            "graded_source_count": len(graded_sources),
            "high_grade_source_count": len(high_grade_sources),
            "claim_count": len(active_claims),
            "supported_claim_count": len(supported_claims),
            "unsupported_claim_count": len(unsupported_claims),
            "high_confidence_claim_count": len(high_confidence_claims),
            "cross_verified_high_confidence_claim_count": len(cross_verified_high_confidence_claims),
            "open_question_count": len(open_questions),
            "high_priority_open_question_count": len(high_priority_open_questions),
            "source_quality_distribution": source_quality_distribution,
        },
        "strengths": strengths,
        "gaps": gaps,
    }


def _executive_summary_markdown(
    paths: ResearchTopicPaths,
    *,
    specialist_report: dict[str, Any],
    claims: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> str:
    lines = [
        f"# {paths.topic} Executive Summary",
        "",
        f"- readiness: `{specialist_report.get('readiness') or 'seed_only'}`",
        f"- target_claim_floor: `{specialist_report.get('target_claim_floor') or 0}`",
        "",
        "## Summary",
    ]
    if specialist_report.get("readiness") == "strong":
        lines.append("- The topic has a strong claim set, multiple high-grade sources, and is ready for downstream writing.")
    elif specialist_report.get("readiness") == "usable":
        lines.append("- The topic is usable for downstream drafting, but still benefits from one more deepening pass before final publication.")
    else:
        lines.append("- The topic is still seed-only. More durable claims and stronger source coverage are required before writing.")

    lines.extend(["", "## Top Claims"])
    if claims:
        for claim in claims[:5]:
            lines.append(f"- [{claim.get('confidence', 'n/a')}] {str(claim.get('claim') or '').strip()}")
    else:
        lines.append("- No durable claims have been promoted yet.")

    lines.extend(["", "## Source Quality"])
    metrics = specialist_report.get("metrics") or {}
    lines.append(
        f"- A/B grade sources: `{metrics.get('high_grade_source_count') or 0}` / total sources: `{metrics.get('source_count') or 0}`"
    )
    quality_distribution = metrics.get("source_quality_distribution") or {}
    lines.append(
        "- quality distribution: "
        + ", ".join(f"{grade}={quality_distribution.get(grade, 0)}" for grade in SOURCE_QUALITY_GRADES)
    )

    lines.extend(["", "## Open Questions"])
    unresolved = [
        item for item in questions
        if str(item.get("status") or "open").strip() != "resolved"
    ]
    if unresolved:
        for question in unresolved[:5]:
            lines.append(
                f"- [{question.get('priority', 'n/a')}] {str(question.get('question') or '').strip()}"
            )
    else:
        lines.append("- No unresolved open questions remain.")

    lines.extend(["", "## Recommended Next Move"])
    if specialist_report.get("readiness") == "strong":
        lines.append("- Proceed to downstream writing or content production.")
    elif specialist_report.get("readiness") == "usable":
        lines.append("- Draft from the current claim set, then schedule a focused follow-up pass for stronger chronology or corroboration.")
    else:
        lines.append("- Run another collection and cross-verification pass before drafting.")

    lines.extend(["", "## Top Sources"])
    for source in sources[:5]:
        lines.append(
            f"- [{str(source.get('quality_grade') or 'n/a').strip() or 'n/a'}] {str(source.get('title') or '').strip()} · {str(source.get('source_url') or '').strip()}"
        )
    if not sources:
        lines.append("- No durable sources registered yet.")
    lines.append("")
    return "\n".join(lines)


def _frontmatter_block(data: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in data.items():
        lines.extend(_yaml_lines(key, value))
    lines.append("---")
    return "\n".join(lines)


def _yaml_lines(key: str, value: Any) -> list[str]:
    if isinstance(value, list):
        if not value:
            return [f"{key}: []"]
        output = [f"{key}:"]
        for item in value:
            output.append(f"  - {json.dumps(str(item), ensure_ascii=False)}")
        return output
    if isinstance(value, bool):
        return [f"{key}: {'true' if value else 'false'}"]
    if isinstance(value, (int, float)):
        return [f"{key}: {value}"]
    return [f"{key}: {json.dumps(str(value), ensure_ascii=False)}"]


def _write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _load_body(inline_value: str, file_value: str) -> str:
    if str(file_value).strip():
        return Path(file_value).expanduser().resolve().read_text(encoding="utf-8")
    return str(inline_value).strip()


def _resolve_asset_file_path(*, packet_path: Path, raw_value: str) -> str:
    text = str(raw_value).strip()
    if not text:
        return ""
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        candidate = (packet_path.parent / candidate).resolve()
    return str(candidate)


def _optional_text(value: str) -> Optional[str]:
    import unicodedata
    text = unicodedata.normalize("NFC", str(value)).strip()
    return text or None


def _effective_vault_dir(value: str) -> Optional[Path]:
    text = str(value).strip()
    return Path(text).expanduser().resolve() if text else None


def _normalize_run_stage(value: str) -> str:
    stage = str(value).strip()
    if not stage:
        raise ValueError("`stage` is required.")
    if stage not in RUN_STAGES:
        raise ValueError(f"Unsupported stage `{stage}`. Expected one of: {', '.join(RUN_STAGES)}")
    return stage


def _normalize_run_status(value: str) -> str:
    status = str(value).strip() or "active"
    if status not in RUN_STATUSES:
        raise ValueError(f"Unsupported status `{status}`. Expected one of: {', '.join(RUN_STATUSES)}")
    return status


def _normalize_quality_grade(value: str) -> str:
    grade = str(value).strip().upper()
    if not grade:
        return ""
    if grade not in SOURCE_QUALITY_GRADES:
        raise ValueError(f"Unsupported quality grade `{grade}`. Expected one of: {', '.join(SOURCE_QUALITY_GRADES)}")
    return grade


def _default_research_root() -> Path:
    direct_root = os.getenv("LLM_WIKI_RESEARCH_DIR") or os.getenv("RESEARCH_WIKI_ROOT")
    if direct_root:
        path = Path(direct_root).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    raise EnvironmentError(
        "No research root configured. Pass --root-dir or export LLM_WIKI_RESEARCH_DIR."
    )


def _clean_list(values: Optional[List[str]]) -> List[str]:
    return [text for text in (str(value).strip() for value in values or []) if text]


def _normalize_asset_suffix(suffix: str, mime_type: str) -> str:
    normalized = str(suffix or "").strip().lower()
    if not normalized:
        normalized = mimetypes.guess_extension(mime_type, strict=False) or ""
    if normalized == ".jpe":
        normalized = ".jpg"
    if normalized and not normalized.startswith("."):
        normalized = f".{normalized}"
    return normalized or ".bin"


def _persist_image_asset(
    *,
    research_root: Path,
    run_dir: Path,
    image_id: str,
    asset_url: str,
    asset_file_path: str,
    mime_type: str,
) -> dict[str, str]:
    if not asset_url and not asset_file_path:
        return {
            "local_asset_path": "",
            "asset_sha256": "",
            "mime_type": mime_type,
            "asset_status": "not_requested",
            "asset_error": "",
        }

    assets_dir = run_dir / "image_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    try:
        detected_mime_type = mime_type
        payload = b""

        if asset_file_path:
            source_path = Path(asset_file_path).expanduser()
            if not source_path.is_absolute():
                source_path = source_path.resolve()
            if not source_path.exists():
                raise FileNotFoundError(f"Asset file not found: {source_path}")
            detected_mime_type = detected_mime_type or (mimetypes.guess_type(source_path.name)[0] or "")
            suffix = _normalize_asset_suffix(source_path.suffix, detected_mime_type)
            target_path = assets_dir / f"{image_id}{suffix}"
            shutil.copy2(source_path, target_path)
            payload = target_path.read_bytes()
        else:
            parsed = urlparse(asset_url)
            if parsed.scheme == "file":
                source_path = Path(unquote(parsed.path)).expanduser()
                if not source_path.exists():
                    raise FileNotFoundError(f"Asset file not found: {source_path}")
                detected_mime_type = detected_mime_type or (mimetypes.guess_type(source_path.name)[0] or "")
                suffix = _normalize_asset_suffix(source_path.suffix, detected_mime_type)
                target_path = assets_dir / f"{image_id}{suffix}"
                shutil.copy2(source_path, target_path)
                payload = target_path.read_bytes()
            else:
                request = Request(asset_url, headers={"User-Agent": "ResearchAgent/0.1"})
                with urlopen(request, timeout=30) as response:
                    payload = response.read()
                    detected_mime_type = detected_mime_type or response.headers.get_content_type() or ""
                suffix = _normalize_asset_suffix(Path(unquote(parsed.path)).suffix, detected_mime_type)
                target_path = assets_dir / f"{image_id}{suffix}"
                target_path.write_bytes(payload)

        return {
            "local_asset_path": _relative_to_root(target_path, research_root),
            "asset_sha256": hashlib.sha256(payload).hexdigest(),
            "mime_type": detected_mime_type,
            "asset_status": "saved",
            "asset_error": "",
        }
    except Exception as exc:
        return {
            "local_asset_path": "",
            "asset_sha256": "",
            "mime_type": mime_type,
            "asset_status": "failed",
            "asset_error": str(exc),
        }


def _merge_reference_ids(
    *,
    explicit_ids: List[str],
    reference_keys: List[str],
    key_map: dict[str, str],
) -> List[str]:
    merged = list(explicit_ids)
    for key in reference_keys:
        mapped = key_map.get(key)
        if mapped and mapped not in merged:
            merged.append(mapped)
    return merged


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _upsert_jsonl(path: Path, key_fields: list[str], record: dict[str, Any]) -> None:
    rows = _load_jsonl(path)
    replaced = False
    for index, current in enumerate(rows):
        if all(str(current.get(field, "")) == str(record.get(field, "")) for field in key_fields):
            rows[index] = record
            replaced = True
            break
    if not replaced:
        rows.append(record)
    payload = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")


def _append_markdown_block(path: Path, heading: str, bullets: list[str]) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    block = "\n".join(["", heading, "", *bullets, ""])
    path.write_text(existing.rstrip() + block, encoding="utf-8")


def _upsert_markdown_section(path: Path, heading: str, bullets: list[str]) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    block = "\n".join([heading, "", *bullets, ""]).rstrip()
    pattern = re.compile(rf"(^|\n){re.escape(heading)}\n.*?(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
    if pattern.search(existing):
        updated = pattern.sub(lambda match: f"{match.group(1)}{block}\n", existing, count=1)
        path.write_text(updated.rstrip() + "\n", encoding="utf-8")
        return
    _append_markdown_block(path, heading, bullets)


def _append_log_entry(paths: ResearchTopicPaths, *, title: str, bullets: list[str]) -> None:
    _append_markdown_block(paths.wiki_dir / "log.md", f"## {_now_iso()} · {title}", bullets)


def _markdown_body(path: Path) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        parts = text.split("\n---\n", 1)
        if len(parts) == 2:
            return parts[1].strip()
    return text.strip()


def _load_run_state(paths: ResearchTopicPaths, run_id: str) -> dict[str, Any]:
    try:
        run_dir = _existing_run_dir(paths, run_id)
    except FileNotFoundError:
        return {}
    state_path = run_dir / "state.json"
    if not state_path.exists():
        return {}
    return json.loads(state_path.read_text(encoding="utf-8"))


def _latest_run_record(paths: ResearchTopicPaths, runs: list[dict[str, Any]]) -> dict[str, Any]:
    latest_run_path = paths.manifests_dir / "latest_run.txt"
    latest_run_id = latest_run_path.read_text(encoding="utf-8").strip() if latest_run_path.exists() else ""
    if latest_run_id:
        state = _load_run_state(paths, latest_run_id)
        if state:
            return state
        for run in runs:
            if str(run.get("run_id") or "").strip() == latest_run_id:
                return run
    return runs[-1] if runs else {}


def _slug_variants(value: str) -> list[str]:
    text = str(value).strip()
    if not text:
        return []
    variants: list[str] = []
    for candidate in [text, text.replace("-", "_"), text.replace("_", "-")]:
        if candidate and candidate not in variants:
            variants.append(candidate)
    return variants


def _candidate_raw_dirs(paths: ResearchTopicPaths, run_id: str) -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()
    for slug in _slug_variants(paths.raw_slug) + _slug_variants(paths.topic_slug):
        candidate = paths.research_root / "raw" / slug / run_id
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(candidate)
    return candidates


def _existing_run_dir(paths: ResearchTopicPaths, run_id: str) -> Path:
    normalized_run_id = str(run_id).strip()
    if not normalized_run_id:
        raise ValueError("`run_id` is required.")
    for run_dir in _candidate_raw_dirs(paths, normalized_run_id):
        if run_dir.exists():
            return run_dir
    raise FileNotFoundError(f"Run directory not found for slugs raw={paths.raw_slug}, topic={paths.topic_slug}, run_id={normalized_run_id}")


def _timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_record_id(prefix: str, *parts: str) -> str:
    cleaned = [str(part).strip() for part in parts if str(part).strip()]
    seed = "||".join(cleaned) or prefix
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
    slug = _safe_slug(cleaned[0] if cleaned else prefix)[:48]
    return f"{prefix}_{slug}_{digest}"


def _safe_slug(value: str) -> str:
    import unicodedata
    value = unicodedata.normalize("NFC", value)
    text = re.sub(r"[^0-9A-Za-z가-힣_-]+", "-", value.strip())
    text = re.sub(r"-{2,}", "-", text).strip("-_")
    return text or "untitled"


def _relative_to_root(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def _issue(level: str, message: str) -> dict[str, str]:
    return {"level": level, "message": message}


def _lint_payload(paths: ResearchTopicPaths, issues: list[dict[str, str]]) -> dict[str, Any]:
    error_count = sum(1 for issue in issues if issue["level"] == "error")
    warning_count = sum(1 for issue in issues if issue["level"] == "warning")
    return {
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "valid": error_count == 0,
        "error_count": error_count,
        "warning_count": warning_count,
        "issues": issues,
    }


if __name__ == "__main__":
    main()

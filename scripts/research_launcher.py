#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

import research_discovery as rd
import research_query_planner as qp
import research_vault as rv


DEFAULT_ASSIGNMENTS = (
    {
        "role": "web-explorer",
        "axis": "official sources, current reporting, and public web evidence",
        "focus": "Prioritize primary sources, institutions, datasets, and high-authority web material.",
    },
    {
        "role": "academic-explorer",
        "axis": "papers, technical documents, and research-grade evidence",
        "focus": "Prioritize peer-reviewed, institutional, or technically rigorous material.",
    },
    {
        "role": "literature-explorer",
        "axis": "long-form reports, archives, and narrative context",
        "focus": "Prioritize long-form sources that improve chronology, interpretation, and context.",
    },
    {
        "role": "image-curator",
        "axis": "images, diagrams, maps, and archival visuals",
        "focus": "Collect evidential visuals with creator, license, and claim/page linkage where possible.",
    },
)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    vault_dir = rv._effective_vault_dir(args.vault_dir)

    if args.command == "prepare-session":
        payload = prepare_session(
            topic=args.topic,
            query=args.query,
            run_id=rv._optional_text(args.run_id),
            topic_slug=rv._optional_text(args.topic_slug),
            entity_slug=rv._optional_text(args.entity_slug),
            section_slug=rv._optional_text(args.section_slug),
            vault_dir=vault_dir,
            downstream_use=args.downstream_use,
            must_answer=args.must_answer,
            excluded_scope=args.exclude,
            notes=args.notes,
            custom_assignments=args.assignment,
            run_discovery=args.discover,
            max_per_lane=args.max_per_lane,
            expansion_rounds=args.expansion_rounds,
        )
    elif args.command == "run-discovery":
        payload = run_discovery_session(
            topic=args.topic,
            run_id=args.run_id,
            topic_slug=rv._optional_text(args.topic_slug),
            vault_dir=vault_dir,
            max_per_lane=args.max_per_lane,
            expansion_rounds=args.expansion_rounds,
            refresh_plan=args.refresh_plan,
        )
    elif args.command == "ingest-bundle":
        payload = ingest_bundle(
            topic=args.topic,
            run_id=args.run_id,
            topic_slug=rv._optional_text(args.topic_slug),
            vault_dir=vault_dir,
            refresh_after_ingest=args.refresh,
            force=args.force,
        )
    elif args.command == "status-session":
        payload = session_status(
            topic=args.topic,
            run_id=args.run_id,
            topic_slug=rv._optional_text(args.topic_slug),
            vault_dir=vault_dir,
        )
    elif args.command == "finalize-session":
        payload = finalize_session(
            topic=args.topic,
            run_id=args.run_id,
            topic_slug=rv._optional_text(args.topic_slug),
            vault_dir=vault_dir,
            notes=args.notes,
        )
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research_launcher.py",
        description="Prepare and finalize end-to-end research sessions on top of the llm-wiki vault runtime.",
    )
    subparsers = parser.add_subparsers(dest="command")

    prepare_parser = subparsers.add_parser(
        "prepare-session",
        help="Initialize a run, mark question refinement complete, and emit a prompt bundle for parallel research.",
    )
    _add_topic_args(prepare_parser)
    prepare_parser.add_argument("--query", required=True, help="Primary research query for the run")
    prepare_parser.add_argument("--run-id", default="", help="Optional explicit run id")
    prepare_parser.add_argument("--entity-slug", default="", help="Optional canonical entity slug for raw run storage")
    prepare_parser.add_argument("--section-slug", default="", help="Optional section slug recorded in run metadata")
    prepare_parser.add_argument("--downstream-use", default="", help="How the topic will be used later")
    prepare_parser.add_argument("--must-answer", action="append", default=[], help="Question that must be answered; repeatable")
    prepare_parser.add_argument("--exclude", action="append", default=[], help="Scope exclusion; repeatable")
    prepare_parser.add_argument("--assignment", action="append", default=[], help="Custom assignment: role|axis|focus")
    prepare_parser.add_argument("--notes", default="", help="Optional operator note stored in the run manifest")
    prepare_parser.add_argument("--discover", action="store_true", help="Run lane-based discovery immediately after preparing the session bundle")
    prepare_parser.add_argument("--max-per-lane", type=int, default=5, help="Maximum discovery candidates kept per lane")
    prepare_parser.add_argument("--expansion-rounds", type=int, default=0, help="Optional discovery expansion rounds to run after the seed pass")

    discovery_parser = subparsers.add_parser(
        "run-discovery",
        help="Load a prepared session bundle, refresh the research plan if requested, and write lane-based discovery outputs.",
    )
    _add_topic_args(discovery_parser)
    discovery_parser.add_argument("--run-id", required=True)
    discovery_parser.add_argument("--max-per-lane", type=int, default=5, help="Maximum discovery candidates kept per lane")
    discovery_parser.add_argument("--expansion-rounds", type=int, default=0, help="Optional discovery expansion rounds to run after the seed pass")
    discovery_parser.add_argument("--refresh-plan", action="store_true", help="Rebuild research_plan.json from the current session metadata before discovery")

    ingest_parser = subparsers.add_parser(
        "ingest-bundle",
        help="Ingest every non-empty packet in a session bundle and advance the run stage.",
    )
    _add_topic_args(ingest_parser)
    ingest_parser.add_argument("--run-id", required=True)
    ingest_parser.add_argument("--refresh", action="store_true", help="Refresh the topic snapshot after bundle ingestion")
    ingest_parser.add_argument("--force", action="store_true", help="Reingest packets even if they were already recorded")

    status_parser = subparsers.add_parser(
        "status-session",
        help="Inspect the session bundle, packet readiness, and recommended next step for a run.",
    )
    _add_topic_args(status_parser)
    status_parser.add_argument("--run-id", required=True)

    finalize_parser = subparsers.add_parser(
        "finalize-session",
        help="Refresh snapshot, lint the topic, and mark packaging complete when lint has no errors.",
    )
    _add_topic_args(finalize_parser)
    finalize_parser.add_argument("--run-id", required=True)
    finalize_parser.add_argument("--notes", default="", help="Optional finalization note")

    return parser


def prepare_session(
    *,
    topic: str,
    query: str,
    run_id: Optional[str],
    topic_slug: Optional[str],
    entity_slug: Optional[str],
    section_slug: Optional[str],
    vault_dir: Optional[Path],
    downstream_use: str,
    must_answer: list[str],
    excluded_scope: list[str],
    notes: str,
    custom_assignments: list[str],
    run_discovery: bool = False,
    max_per_lane: int = 5,
    expansion_rounds: int = 0,
) -> dict[str, Any]:
    assignments = _assignments_payload(custom_assignments)
    planned_agents = [assignment["role"] for assignment in assignments] + ["cross-verifier"]
    rv.ensure_research_topic(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    run_payload = rv.start_research_run(
        topic,
        run_id=run_id,
        query=query,
        focus=[assignment["axis"] for assignment in assignments],
        planned_agents=planned_agents,
        notes=notes,
        topic_slug=topic_slug,
        entity_slug=entity_slug,
        section_slug=section_slug,
        vault_dir=vault_dir,
    )
    effective_run_id = run_payload["run_id"]
    paths = rv.resolve_topic_paths(topic, topic_slug=topic_slug, entity_slug=entity_slug, vault_dir=vault_dir)
    run_dir = Path(run_payload["run_dir"])

    refinement_note = _render_refinement_note(
        query=query,
        downstream_use=downstream_use,
        must_answer=must_answer,
        excluded_scope=excluded_scope,
        notes=notes,
    )
    rv.set_run_stage(
        topic,
        run_id=effective_run_id,
        stage="question-refinement",
        status="active",
        notes=refinement_note,
        mark_complete=True,
        topic_slug=topic_slug,
        entity_slug=entity_slug,
        vault_dir=vault_dir,
    )
    planning_state = rv.set_run_stage(
        topic,
        run_id=effective_run_id,
        stage="search-planning",
        status="active",
        notes="Prompt bundle generated and ready for packet-based parallel collection.",
        topic_slug=topic_slug,
        entity_slug=entity_slug,
        vault_dir=vault_dir,
    )

    bundle_dir = run_dir / "artifacts" / "session_bundle"
    subagent_dir = bundle_dir / "subagents"
    packet_dir = bundle_dir / "packet_targets"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    subagent_dir.mkdir(parents=True, exist_ok=True)
    packet_dir.mkdir(parents=True, exist_ok=True)

    session_plan = {
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "entity_slug": str(entity_slug or paths.raw_slug).strip(),
        "section_slug": str(section_slug or "").strip(),
        "raw_slug": paths.raw_slug,
        "run_id": effective_run_id,
        "query": query.strip(),
        "downstream_use": downstream_use.strip(),
        "must_answer": rv._clean_list(must_answer),
        "excluded_scope": rv._clean_list(excluded_scope),
        "notes": notes.strip(),
        "research_plan_path": "",
        "discovery": {},
        "assignments": [],
        "verifier": {},
    }

    main_agent_path = bundle_dir / "main_agent.md"
    planner_path = bundle_dir / "session_brief.md"
    planner_json_path = bundle_dir / "session_plan.json"

    for index, assignment in enumerate(assignments, start=1):
        slug = _assignment_slug(index, assignment["role"], assignment["axis"])
        packet_path = packet_dir / f"{slug}.json"
        prompt_path = subagent_dir / f"{slug}.md"
        packet_stub = _packet_stub(
            packet_id=f"{paths.topic_slug}-{assignment['role']}-{index:02d}",
            axis=assignment["axis"],
            agent_role=assignment["role"],
        )
        packet_path.write_text(json.dumps(packet_stub, ensure_ascii=False, indent=2), encoding="utf-8")
        prompt_path.write_text(
            _render_subagent_prompt(
                topic=paths.topic,
                query=query,
                downstream_use=downstream_use,
                must_answer=must_answer,
                excluded_scope=excluded_scope,
                assignment=assignment,
                packet_path=packet_path,
            ),
            encoding="utf-8",
        )
        session_plan["assignments"].append(
            {
                **assignment,
                "prompt_path": str(prompt_path),
                "packet_target_path": str(packet_path),
            }
        )

    verifier_packet_path = packet_dir / "cross_verifier.json"
    verifier_prompt_path = bundle_dir / "cross_verifier.md"
    verifier_packet_path.write_text(
        json.dumps(
            _packet_stub(
                packet_id=f"{paths.topic_slug}-cross-verifier",
                axis="cross-verification",
                agent_role="cross-verifier",
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    verifier_prompt_path.write_text(
        _render_verifier_prompt(
            topic=paths.topic,
            query=query,
            downstream_use=downstream_use,
            must_answer=must_answer,
            verifier_packet_path=verifier_packet_path,
        ),
        encoding="utf-8",
    )
    session_plan["verifier"] = {
        "role": "cross-verifier",
        "prompt_path": str(verifier_prompt_path),
        "packet_target_path": str(verifier_packet_path),
    }

    research_plan = _build_session_research_plan(
        topic=paths.topic,
        query=query,
        downstream_use=downstream_use,
        must_answer=must_answer,
        excluded_scope=excluded_scope,
        paths=paths,
    )
    research_plan_path = bundle_dir / "research_plan.json"
    research_plan_path.write_text(json.dumps(research_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    session_plan["research_plan_path"] = str(research_plan_path)
    if run_discovery:
        session_plan["discovery"] = rd.write_discovery_outputs(
            research_plan,
            bundle_dir / "discovery",
            max_per_lane=max_per_lane,
            expansion_rounds=expansion_rounds,
        )
    _write_session_bundle_files(
        topic=paths.topic,
        query=query,
        run_id=effective_run_id,
        bundle_dir=bundle_dir,
        planner_path=planner_path,
        planner_json_path=planner_json_path,
        main_agent_path=main_agent_path,
        session_plan=session_plan,
    )

    rv._append_log_entry(
        paths,
        title=f"Session bundle prepared: {effective_run_id}",
        bullets=[
            f"bundle_dir: `{rv._relative_to_root(bundle_dir, paths.research_root)}`",
            f"subagent_count: `{len(assignments)}`",
            f"research_plan: `{rv._relative_to_root(research_plan_path, paths.research_root)}`",
            f"verifier_prompt: `{rv._relative_to_root(verifier_prompt_path, paths.research_root)}`",
        ] + (
            [f"discovery_summary: `{rv._relative_to_root(Path(session_plan['discovery']['discovery_summary']), paths.research_root)}`"]
            if session_plan["discovery"]
            else []
        ),
    )

    return {
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "entity_slug": str(entity_slug or paths.raw_slug).strip(),
        "section_slug": str(section_slug or "").strip(),
        "raw_slug": paths.raw_slug,
        "run_id": effective_run_id,
        "stage": planning_state["stage"],
        "status": planning_state["status"],
        "bundle_dir": str(bundle_dir),
        "main_agent_path": str(main_agent_path),
        "session_brief_path": str(planner_path),
        "session_plan_path": str(planner_json_path),
        "research_plan_path": str(research_plan_path),
        "discovery": session_plan["discovery"],
        "assignments": session_plan["assignments"],
        "verifier": session_plan["verifier"],
    }


def run_discovery_session(
    *,
    topic: str,
    run_id: str,
    topic_slug: Optional[str],
    vault_dir: Optional[Path],
    max_per_lane: int,
    expansion_rounds: int,
    refresh_plan: bool,
) -> dict[str, Any]:
    paths = rv.resolve_topic_paths(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    bundle_dir = _bundle_dir(paths, run_id)
    session_plan = _load_session_plan(bundle_dir)
    research_plan_path = Path(session_plan.get("research_plan_path") or bundle_dir / "research_plan.json")
    if refresh_plan or not research_plan_path.exists():
        research_plan = _build_session_research_plan(
            topic=paths.topic,
            query=str(session_plan.get("query") or "").strip(),
            downstream_use=str(session_plan.get("downstream_use") or "").strip(),
            must_answer=rv._clean_list(session_plan.get("must_answer") or []),
            excluded_scope=rv._clean_list(session_plan.get("excluded_scope") or []),
            paths=paths,
        )
        research_plan_path.write_text(json.dumps(research_plan, ensure_ascii=False, indent=2), encoding="utf-8")
        session_plan["research_plan_path"] = str(research_plan_path)
    else:
        research_plan = json.loads(research_plan_path.read_text(encoding="utf-8"))

    discovery_outputs = rd.write_discovery_outputs(
        research_plan,
        bundle_dir / "discovery",
        max_per_lane=max_per_lane,
        expansion_rounds=expansion_rounds,
    )
    session_plan["discovery"] = discovery_outputs
    _write_session_bundle_files(
        topic=paths.topic,
        query=str(session_plan.get("query") or "").strip(),
        run_id=run_id,
        bundle_dir=bundle_dir,
        planner_path=bundle_dir / "session_brief.md",
        planner_json_path=bundle_dir / "session_plan.json",
        main_agent_path=bundle_dir / "main_agent.md",
        session_plan=session_plan,
    )
    summary = json.loads(Path(discovery_outputs["discovery_summary"]).read_text(encoding="utf-8"))
    return {
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "run_id": run_id,
        "bundle_dir": str(bundle_dir),
        "research_plan_path": str(research_plan_path),
        "discovery": discovery_outputs,
        "summary": summary.get("summary") or {},
    }


def finalize_session(
    *,
    topic: str,
    run_id: str,
    topic_slug: Optional[str],
    vault_dir: Optional[Path],
    notes: str,
) -> dict[str, Any]:
    snapshot = rv.refresh_topic_snapshot(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    lint = rv.lint_research_topic(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    status = session_status(topic=topic, run_id=run_id, topic_slug=topic_slug, vault_dir=vault_dir)
    readiness = str(snapshot.get("specialist_readiness") or "seed_only")
    if (
        lint.get("valid")
        and status.get("recommended_next_step") == "finalize-session"
        and readiness in {"usable", "strong"}
    ):
        final_state = rv.set_run_stage(
            topic,
            run_id=run_id,
            stage="packaging",
            status="completed",
            notes=notes.strip() or f"Snapshot refreshed, lint passed, and specialist readiness is `{readiness}`.",
            mark_complete=True,
            topic_slug=topic_slug,
            vault_dir=vault_dir,
        )
    else:
        blocker = status.get("recommended_next_step") or "resolve-session-gaps"
        final_state = rv.set_run_stage(
            topic,
            run_id=run_id,
            stage="quality-assurance",
            status="blocked",
            notes=notes.strip() or f"Packaging blocked. Next step: {blocker}. Specialist readiness: `{readiness}`.",
            topic_slug=topic_slug,
            vault_dir=vault_dir,
        )
    final_snapshot = rv.refresh_topic_snapshot(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    final_lint = rv.lint_research_topic(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    final_status = session_status(topic=topic, run_id=run_id, topic_slug=topic_slug, vault_dir=vault_dir)
    return {
        "snapshot": final_snapshot,
        "lint": final_lint,
        "status": final_status,
        "run_state": final_state,
    }


def ingest_bundle(
    *,
    topic: str,
    run_id: str,
    topic_slug: Optional[str],
    vault_dir: Optional[Path],
    refresh_after_ingest: bool,
    force: bool,
) -> dict[str, Any]:
    paths = rv.resolve_topic_paths(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    bundle_dir = _bundle_dir(paths, run_id)
    plan = _load_session_plan(bundle_dir)
    packet_dir = bundle_dir / "packet_targets"

    ingested_packets: list[dict[str, Any]] = []
    skipped_packets: list[dict[str, Any]] = []
    verifier_ingested = False
    explorer_ingested = False

    for packet_path in sorted(packet_dir.glob("*.json")):
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet_id = str(packet.get("packet_id") or packet_path.stem).strip()
        record_path = _packet_record_path(paths, run_id, packet_id)
        if _is_packet_empty(packet):
            skipped_packets.append(
                {
                    "packet_path": str(packet_path),
                    "packet_id": packet_id or packet_path.stem,
                    "reason": "empty",
                }
            )
            continue
        if record_path.exists() and not force:
            skipped_packets.append(
                {
                    "packet_path": str(packet_path),
                    "packet_id": packet_id or packet_path.stem,
                    "reason": "already-ingested",
                }
            )
            continue
        payload = rv.ingest_packet(
            topic,
            run_id=run_id,
            packet_path=packet_path,
            topic_slug=topic_slug,
            vault_dir=vault_dir,
            refresh_after_ingest=False,
        )
        ingested_packets.append(
            {
                "packet_path": str(packet_path),
                "packet_id": payload["packet_id"],
                "source_count": len(payload["source_ids"]),
                "claim_count": len(payload["claim_ids"]),
                "image_count": len(payload["image_ids"]),
                "question_count": len(payload["question_ids"]),
            }
        )
        if str(packet.get("agent_role") or "").strip() == "cross-verifier":
            verifier_ingested = True
        else:
            explorer_ingested = True

    next_state: dict[str, Any] = {}
    if verifier_ingested:
        next_state = rv.set_run_stage(
            topic,
            run_id=run_id,
            stage="knowledge-synthesis",
            status="active",
            notes="Verifier packet ingested. Ready for synthesis and QA.",
            mark_complete=True,
            topic_slug=topic_slug,
            vault_dir=vault_dir,
        )
    elif explorer_ingested:
        next_state = rv.set_run_stage(
            topic,
            run_id=run_id,
            stage="cross-verification",
            status="active",
            notes="Explorer packets ingested. Run the verifier before synthesis.",
            mark_complete=True,
            topic_slug=topic_slug,
            vault_dir=vault_dir,
        )
    else:
        next_state = _load_run_state(paths, run_id)

    payload: dict[str, Any] = {
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "run_id": run_id,
        "bundle_dir": str(bundle_dir),
        "ingested_packets": ingested_packets,
        "skipped_packets": skipped_packets,
        "run_state": next_state,
        "session_plan_path": str(bundle_dir / "session_plan.json"),
    }
    if refresh_after_ingest:
        payload["snapshot"] = rv.refresh_topic_snapshot(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    payload["status"] = session_status(topic=topic, run_id=run_id, topic_slug=topic_slug, vault_dir=vault_dir)
    return payload


def session_status(
    *,
    topic: str,
    run_id: str,
    topic_slug: Optional[str],
    vault_dir: Optional[Path],
) -> dict[str, Any]:
    paths = rv.resolve_topic_paths(topic, topic_slug=topic_slug, vault_dir=vault_dir)
    bundle_dir = _bundle_dir(paths, run_id)
    plan = _load_session_plan(bundle_dir)
    packet_statuses: list[dict[str, Any]] = []

    for assignment in plan.get("assignments") or []:
        packet_statuses.append(_packet_status(paths, run_id, Path(assignment["packet_target_path"]), role=assignment["role"]))

    verifier_info = plan.get("verifier") or {}
    verifier_status = _packet_status(
        paths,
        run_id,
        Path(verifier_info["packet_target_path"]),
        role=str(verifier_info.get("role") or "cross-verifier"),
    ) if verifier_info else {}

    run_state = _load_run_state(paths, run_id)
    sources = rv._load_jsonl(paths.manifests_dir / "sources.jsonl")
    claims = rv._load_jsonl(paths.manifests_dir / "claims.jsonl")
    images = rv._load_jsonl(paths.manifests_dir / "images.jsonl")
    questions = rv._load_jsonl(paths.manifests_dir / "open_questions.jsonl")
    specialist_snapshot = rv.refresh_topic_snapshot(topic, topic_slug=topic_slug, vault_dir=vault_dir)

    explorer_ready_uningested = [item for item in packet_statuses if item["ready_to_ingest"] and not item["already_ingested"]]
    missing_explorer_packets = [item for item in packet_statuses if not item["ready_to_ingest"] and not item["already_ingested"]]
    explorer_ingested = [item for item in packet_statuses if item["already_ingested"]]
    verifier_ready = bool(verifier_status) and verifier_status.get("ready_to_ingest", False)
    verifier_ingested = bool(verifier_status) and verifier_status.get("already_ingested", False)
    verifier_ready_uningested = bool(verifier_status) and verifier_ready and not verifier_ingested
    discovery = plan.get("discovery") or {}
    discovery_summary_path = str(discovery.get("discovery_summary") or "").strip()
    discovery_summary = {}
    if discovery_summary_path and Path(discovery_summary_path).exists():
        discovery_summary = json.loads(Path(discovery_summary_path).read_text(encoding="utf-8"))

    if str(run_state.get("stage") or "") == "packaging" and str(run_state.get("status") or "") == "completed":
        recommended_next_step = "complete"
    elif explorer_ready_uningested:
        recommended_next_step = "ingest-bundle"
    elif missing_explorer_packets:
        recommended_next_step = "collect-subagent-packets"
    elif verifier_ready_uningested:
        recommended_next_step = "ingest-verifier-packet"
    elif not verifier_ingested:
        recommended_next_step = "run-cross-verifier"
    elif str(specialist_snapshot.get("specialist_readiness") or "seed_only") == "seed_only":
        recommended_next_step = "strengthen-claim-set"
    else:
        recommended_next_step = "finalize-session"

    return {
        "topic": paths.topic,
        "topic_slug": paths.topic_slug,
        "run_id": run_id,
        "bundle_dir": str(bundle_dir),
        "run_state": run_state,
        "packet_statuses": packet_statuses,
        "verifier_status": verifier_status,
        "counts": {
            "sources": len(sources),
            "claims": len(claims),
            "images": len(images),
            "open_questions": len(questions),
            "explorer_packets_ingested": len(explorer_ingested),
        },
        "specialist_readiness": specialist_snapshot.get("specialist_readiness") or "seed_only",
        "specialist_report_path": specialist_snapshot.get("specialist_report_path") or "",
        "executive_summary_path": specialist_snapshot.get("executive_summary_path") or "",
        "research_plan_path": str(plan.get("research_plan_path") or ""),
        "discovery": {
            "discovery_summary_path": discovery_summary_path,
            "candidate_count": int((discovery_summary.get("summary") or {}).get("candidate_count") or 0),
            "packet_count": int((discovery_summary.get("summary") or {}).get("packet_count") or 0),
            "query_expansion_count": int((discovery_summary.get("summary") or {}).get("query_expansion_count") or 0),
        },
        "recommended_next_step": recommended_next_step,
    }


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


def _assignments_payload(custom_assignments: list[str]) -> list[dict[str, str]]:
    if not custom_assignments:
        return [dict(item) for item in DEFAULT_ASSIGNMENTS]
    parsed: list[dict[str, str]] = []
    for raw in custom_assignments:
        parts = [part.strip() for part in str(raw).split("|")]
        if len(parts) != 3 or not all(parts):
            raise ValueError("Each --assignment must use the form `role|axis|focus`.")
        parsed.append({"role": parts[0], "axis": parts[1], "focus": parts[2]})
    return parsed


def _assignment_slug(index: int, role: str, axis: str) -> str:
    return f"{index:02d}_{rv._safe_slug(role)}_{rv._safe_slug(axis)[:40]}".strip("_")


def _packet_stub(*, packet_id: str, axis: str, agent_role: str) -> dict[str, Any]:
    return {
        "packet_id": packet_id,
        "axis": axis,
        "agent_role": agent_role,
        "summary": "",
        "sources": [],
        "claims": [],
        "images": [],
        "open_questions": [],
    }


def _render_refinement_note(
    *,
    query: str,
    downstream_use: str,
    must_answer: list[str],
    excluded_scope: list[str],
    notes: str,
) -> str:
    lines = [
        f"query: {query.strip()}",
        f"downstream_use: {downstream_use.strip() or 'n/a'}",
        f"must_answer: {', '.join(rv._clean_list(must_answer)) or 'n/a'}",
        f"excluded_scope: {', '.join(rv._clean_list(excluded_scope)) or 'n/a'}",
    ]
    if notes.strip():
        lines.append(f"notes: {notes.strip()}")
    return "\n".join(lines)


def _render_session_brief(plan: dict[str, Any]) -> str:
    lines = [
        f"# Session Brief: {plan['topic']}",
        "",
        "## Research Query",
        plan["query"] or "- none",
        "",
        "## Downstream Use",
        plan["downstream_use"] or "- none",
        "",
        "## Must Answer",
    ]
    if plan["must_answer"]:
        lines.extend(f"- {item}" for item in plan["must_answer"])
    else:
        lines.append("- none recorded")
    lines.extend(["", "## Excluded Scope"])
    if plan["excluded_scope"]:
        lines.extend(f"- {item}" for item in plan["excluded_scope"])
    else:
        lines.append("- none recorded")
    lines.extend(["", "## Discovery Assets"])
    lines.append(f"- research_plan_path: `{plan.get('research_plan_path') or 'n/a'}`")
    discovery = plan.get("discovery") or {}
    if discovery:
        lines.append(f"- discovery_candidates: `{discovery.get('discovery_candidates') or 'n/a'}`")
        lines.append(f"- discovery_summary: `{discovery.get('discovery_summary') or 'n/a'}`")
        lines.append(f"- query_expansions: `{discovery.get('query_expansions') or 'n/a'}`")
    else:
        lines.append("- discovery outputs not generated yet")
    lines.extend(["", "## Planned Assignments"])
    for assignment in plan["assignments"]:
        lines.extend(
            [
                f"### {assignment['role']}",
                f"- axis: {assignment['axis']}",
                f"- focus: {assignment['focus']}",
                f"- prompt_path: `{assignment['prompt_path']}`",
                f"- packet_target_path: `{assignment['packet_target_path']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Verifier",
            f"- prompt_path: `{plan['verifier']['prompt_path']}`",
            f"- packet_target_path: `{plan['verifier']['packet_target_path']}`",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_main_agent_bundle(
    *,
    topic: str,
    query: str,
    run_id: str,
    bundle_dir: Path,
    plan: dict[str, Any],
) -> str:
    lines = [
        f"# Main Agent Bundle: {topic}",
        "",
        f"- run_id: `{run_id}`",
        f"- bundle_dir: `{bundle_dir}`",
        f"- query: {query}",
        "",
        "## Execution Order",
        "1. Read `session_brief.md`.",
        "2. Inspect `research_plan.json` and any discovery outputs before dispatching subagents.",
        "3. Dispatch one subagent per assignment using the prompt files below.",
        "4. Save each returned JSON packet to its matching packet target path.",
        "5. Check `research_launcher.py status-session` to see what is still missing.",
        "6. Run `research_launcher.py ingest-bundle` after explorer packets are ready.",
        "7. Run the cross-verifier prompt after the first collection pass.",
        "8. Save the verifier packet and run `research_launcher.py ingest-bundle` again.",
        "9. Run `research_launcher.py finalize-session`.",
        "",
        "## Discovery",
        f"- research_plan: `{plan.get('research_plan_path') or 'n/a'}`",
        f"- discovery_summary: `{(plan.get('discovery') or {}).get('discovery_summary') or 'n/a'}`",
        "",
        "## Subagent Prompts",
    ]
    for assignment in plan["assignments"]:
        lines.extend(
            [
                f"- role: `{assignment['role']}`",
                f"  prompt: `{assignment['prompt_path']}`",
                f"  packet_target: `{assignment['packet_target_path']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Verifier",
            f"- prompt: `{plan['verifier']['prompt_path']}`",
            f"- packet_target: `{plan['verifier']['packet_target_path']}`",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_subagent_prompt(
    *,
    topic: str,
    query: str,
    downstream_use: str,
    must_answer: list[str],
    excluded_scope: list[str],
    assignment: dict[str, str],
    packet_path: Path,
) -> str:
    template = _read_template("subagent-packet-prompt.md")
    lines = [
        f"# {assignment['role']} Assignment",
        "",
        f"- topic: {topic}",
        f"- query: {query}",
        f"- downstream_use: {downstream_use or 'n/a'}",
        f"- packet_target_path: `{packet_path}`",
        f"- axis_focus: {assignment['focus']}",
        "",
        "## Must Answer",
    ]
    if must_answer:
        lines.extend(f"- {item}" for item in rv._clean_list(must_answer))
    else:
        lines.append("- none recorded")
    lines.extend(["", "## Excluded Scope"])
    if excluded_scope:
        lines.extend(f"- {item}" for item in rv._clean_list(excluded_scope))
    else:
        lines.append("- none recorded")
    lines.extend(
        [
            "",
            "## Prompt Template",
            "",
            template.replace("<AXIS>", assignment["axis"]).replace("<ROLE>", assignment["role"]),
            "",
        ]
    )
    return "\n".join(lines)


def _render_verifier_prompt(
    *,
    topic: str,
    query: str,
    downstream_use: str,
    must_answer: list[str],
    verifier_packet_path: Path,
) -> str:
    template = _read_template("cross-verifier-prompt.md")
    lines = [
        "# Cross Verifier Assignment",
        "",
        f"- topic: {topic}",
        f"- query: {query}",
        f"- downstream_use: {downstream_use or 'n/a'}",
        f"- packet_target_path: `{verifier_packet_path}`",
        "",
        "## Must Answer",
    ]
    if must_answer:
        lines.extend(f"- {item}" for item in rv._clean_list(must_answer))
    else:
        lines.append("- none recorded")
    lines.extend(["", "## Prompt Template", "", template, ""])
    return "\n".join(lines)


def _read_template(name: str) -> str:
    template_path = Path(__file__).resolve().parents[1] / "templates" / name
    return template_path.read_text(encoding="utf-8").strip()


def _build_session_research_plan(
    *,
    topic: str,
    query: str,
    downstream_use: str,
    must_answer: list[str],
    excluded_scope: list[str],
    paths: rv.ResearchTopicPaths,
) -> dict[str, Any]:
    existing_sources = rv._load_jsonl(paths.manifests_dir / "sources.jsonl")
    return qp.build_research_plan(
        topic=topic,
        query=query,
        downstream_use=downstream_use,
        must_answer=rv._clean_list(must_answer),
        excluded_scope=rv._clean_list(excluded_scope),
        existing_sources=existing_sources,
    )


def _write_session_bundle_files(
    *,
    topic: str,
    query: str,
    run_id: str,
    bundle_dir: Path,
    planner_path: Path,
    planner_json_path: Path,
    main_agent_path: Path,
    session_plan: dict[str, Any],
) -> None:
    planner_json_path.write_text(json.dumps(session_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    planner_path.write_text(_render_session_brief(session_plan), encoding="utf-8")
    main_agent_path.write_text(
        _render_main_agent_bundle(
            topic=topic,
            query=query,
            run_id=run_id,
            bundle_dir=bundle_dir,
            plan=session_plan,
        ),
        encoding="utf-8",
    )


def _bundle_dir(paths: rv.ResearchTopicPaths, run_id: str) -> Path:
    return rv._existing_run_dir(paths, run_id) / "artifacts" / "session_bundle"


def _load_session_plan(bundle_dir: Path) -> dict[str, Any]:
    plan_path = bundle_dir / "session_plan.json"
    if not plan_path.exists():
        raise FileNotFoundError(f"Session plan not found: {plan_path}")
    return json.loads(plan_path.read_text(encoding="utf-8"))


def _packet_record_path(paths: rv.ResearchTopicPaths, run_id: str, packet_id: str) -> Path:
    return rv._existing_run_dir(paths, run_id) / "artifacts" / "packets" / f"{rv._safe_slug(packet_id)}.json"


def _load_run_state(paths: rv.ResearchTopicPaths, run_id: str) -> dict[str, Any]:
    return rv._load_run_state(paths, run_id)


def _packet_status(paths: rv.ResearchTopicPaths, run_id: str, packet_path: Path, *, role: str) -> dict[str, Any]:
    packet = json.loads(packet_path.read_text(encoding="utf-8")) if packet_path.exists() else {}
    packet_id = str(packet.get("packet_id") or packet_path.stem).strip() or packet_path.stem
    counts = _packet_counts(packet)
    return {
        "role": role,
        "packet_path": str(packet_path),
        "packet_id": packet_id,
        "exists": packet_path.exists(),
        "counts": counts,
        "ready_to_ingest": packet_path.exists() and not _is_packet_empty(packet),
        "already_ingested": _packet_record_path(paths, run_id, packet_id).exists(),
    }


def _packet_counts(packet: dict[str, Any]) -> dict[str, int]:
    return {
        "sources": len(packet.get("sources") or []),
        "claims": len(packet.get("claims") or []),
        "images": len(packet.get("images") or []),
        "open_questions": len(packet.get("open_questions") or []),
    }


def _is_packet_empty(packet: dict[str, Any]) -> bool:
    counts = _packet_counts(packet)
    return all(value == 0 for value in counts.values()) and not str(packet.get("summary") or "").strip()


if __name__ == "__main__":
    main()

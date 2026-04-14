from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import research_lane_tools as lane_tools
from research_source_priors import (
    institutional_domain_bonus,
    institutional_noise_penalty,
    lane_blacklist_terms,
    literature_noise_penalty,
    literature_publisher_bonus,
    media_noise_penalty,
    media_publisher_bonus,
    reference_domain_bonus,
    reference_noise_penalty,
)
from research_source_trust import classify_source_record


JsonFetcher = Callable[[str], dict[str, Any]]
TextFetcher = Callable[[str], str]

DISCOVERY_PACKET_PARALLELISM = 8
PACKET_PRIORITY_ORDER = ("highest", "high", "medium")


def discover_source_candidates(
    research_plan: dict[str, Any],
    *,
    max_per_lane: int = 5,
    expansion_rounds: int = 0,
    fetch_json: JsonFetcher | None = None,
    fetch_text: TextFetcher | None = None,
) -> dict[str, Any]:
    fetch = fetch_json or _fetch_json
    fetch_text_impl = fetch_text or _fetch_text
    seed_packets = build_discovery_packets(research_plan)
    seed_execution = _execute_discovery_packets(
        packets=seed_packets,
        topic=str(research_plan.get("topic") or "").strip(),
        anchor_terms=[str(item).strip() for item in (research_plan.get("anchor_terms") or []) if str(item).strip()],
        focus_terms=[str(item).strip() for item in (research_plan.get("focus_terms") or []) if str(item).strip()],
        max_per_lane=max_per_lane,
        fetch_json=fetch,
        fetch_text=fetch_text_impl,
    )
    candidates = seed_execution["candidates"]
    errors = seed_execution["errors"]
    packet_results = list(seed_execution["packet_results"])

    query_seed_topic = str(research_plan.get("query_topic") or research_plan.get("query") or research_plan.get("topic") or "").strip()
    query_expansions = _build_query_expansions(topic=query_seed_topic, candidates=candidates)
    if expansion_rounds > 0 and query_expansions:
        expansion_packets = build_discovery_packets(research_plan, stage="expansion", query_expansions=query_expansions)
        expansion_execution = _execute_discovery_packets(
            packets=expansion_packets,
            topic=str(research_plan.get("topic") or "").strip(),
            anchor_terms=[str(item).strip() for item in (research_plan.get("anchor_terms") or []) if str(item).strip()],
            focus_terms=[str(item).strip() for item in (research_plan.get("focus_terms") or []) if str(item).strip()],
            max_per_lane=max_per_lane,
            existing_candidates=candidates,
            fetch_json=fetch,
            fetch_text=fetch_text_impl,
        )
        candidates = expansion_execution["candidates"]
        errors = expansion_execution["errors"]
        packet_results.extend(expansion_execution["packet_results"])
        query_expansions = _build_query_expansions(topic=query_seed_topic, candidates=candidates)

    candidates.sort(key=lambda item: item.get("ranking_score") or 0, reverse=True)
    summary = _discovery_summary(
        candidates=candidates,
        packet_results=packet_results,
        query_expansions=query_expansions,
        errors=errors,
    )
    source_note_seeds = _build_source_note_seeds(candidates)
    return {
        "version": "research-discovery-v1",
        "topic": research_plan.get("topic"),
        "query": research_plan.get("query"),
        "parallel_strategy": {
            "packet_parallelism": DISCOVERY_PACKET_PARALLELISM,
            "priority_order": list(PACKET_PRIORITY_ORDER),
        },
        "packets": packet_results,
        "candidates": candidates,
        "query_expansions": query_expansions,
        "source_note_seeds": source_note_seeds,
        "errors": errors,
        "summary": summary,
    }


def write_discovery_outputs(
    research_plan: dict[str, Any],
    output_dir: Path,
    *,
    max_per_lane: int = 5,
    expansion_rounds: int = 0,
    fetch_json: JsonFetcher | None = None,
    fetch_text: TextFetcher | None = None,
) -> dict[str, str]:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result = discover_source_candidates(
        research_plan,
        max_per_lane=max_per_lane,
        expansion_rounds=expansion_rounds,
        fetch_json=fetch_json,
        fetch_text=fetch_text,
    )
    candidates_path = output_dir / "discovered_source_candidates.jsonl"
    note_seeds_path = output_dir / "source_note_seeds.jsonl"
    packets_path = output_dir / "discovery_packets.json"
    strategy_path = output_dir / "parallel_research_strategy.json"
    expansions_path = output_dir / "query_expansions.json"
    summary_path = output_dir / "discovery_summary.json"
    candidates_path.write_text(_to_jsonl(result["candidates"]), encoding="utf-8")
    note_seeds_path.write_text(_to_jsonl(result["source_note_seeds"]), encoding="utf-8")
    packets_path.write_text(json.dumps(result["packets"], ensure_ascii=False, indent=2), encoding="utf-8")
    strategy_path.write_text(json.dumps(result["parallel_strategy"], ensure_ascii=False, indent=2), encoding="utf-8")
    expansions_path.write_text(json.dumps(result["query_expansions"], ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "discovery_candidates": str(candidates_path),
        "source_note_seeds": str(note_seeds_path),
        "discovery_packets": str(packets_path),
        "parallel_research_strategy": str(strategy_path),
        "query_expansions": str(expansions_path),
        "discovery_summary": str(summary_path),
    }


def build_discovery_packets(
    research_plan: dict[str, Any],
    *,
    stage: str = "seed",
    query_expansions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    packet_index = 0
    if query_expansions:
        grouped = _group_expansions_by_lane(query_expansions)
        lanes_by_id = {str(lane.get("lane_id") or "").strip(): lane for lane in (research_plan.get("lanes") or [])}
        for lane_id, entries in grouped.items():
            lane = lanes_by_id.get(lane_id) or {}
            for entry in entries:
                packet_index += 1
                packets.append(
                    {
                        "packet_id": f"{stage}-{lane_id}-{packet_index:03d}",
                        "stage": stage,
                        "lane_id": lane_id,
                        "priority": str(lane.get("priority") or "medium").strip() or "medium",
                        "track_id": str(entry.get("track_id") or "general").strip() or "general",
                        "track_label": str(entry.get("track_label") or "General").strip() or "General",
                        "queries": [str(entry.get("query") or "").strip()],
                        "blacklist_terms": _clean_list(lane.get("blacklist_terms") or lane_blacklist_terms(lane_id)),
                    }
                )
        return _sort_packets(packets)

    for lane in research_plan.get("lanes") or []:
        lane_id = str(lane.get("lane_id") or "").strip()
        if not lane_id or lane_id == "image_evidence":
            continue
        for entry in _lane_query_entries(lane):
            packet_index += 1
            packets.append(
                {
                    "packet_id": f"{stage}-{lane_id}-{packet_index:03d}",
                    "stage": stage,
                    "lane_id": lane_id,
                    "priority": str(lane.get("priority") or "medium").strip() or "medium",
                    "track_id": str(entry.get("track_id") or "general").strip() or "general",
                    "track_label": str(entry.get("track_label") or "General").strip() or "General",
                    "queries": [str(entry.get("query") or "").strip()],
                    "blacklist_terms": _clean_list(lane.get("blacklist_terms") or lane_blacklist_terms(lane_id)),
                }
            )
    return _sort_packets(packets)


def _execute_discovery_packets(
    *,
    packets: list[dict[str, Any]],
    topic: str,
    anchor_terms: list[str],
    focus_terms: list[str],
    max_per_lane: int,
    fetch_json: JsonFetcher,
    fetch_text: TextFetcher,
    existing_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    candidates = [dict(item) for item in (existing_candidates or [])]
    candidate_keys = {
        _candidate_dedupe_key(item): index
        for index, item in enumerate(candidates)
        if _candidate_dedupe_key(item)
    }
    lane_added = _count_by(candidates, "lane_id")
    packet_results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=min(DISCOVERY_PACKET_PARALLELISM, max(len(packets), 1))) as executor:
        future_map = {
            executor.submit(
                _execute_packet,
                packet,
                topic=topic,
                anchor_terms=anchor_terms,
                focus_terms=focus_terms,
                fetch_json=fetch_json,
                fetch_text=fetch_text,
            ): packet
            for packet in packets
        }
        for future in as_completed(future_map):
            packet = future_map[future]
            try:
                packet_result = future.result()
            except Exception as exc:
                packet_results.append(
                    {
                        "packet_id": packet.get("packet_id"),
                        "lane_id": packet.get("lane_id"),
                        "stage": packet.get("stage"),
                        "status": "failed",
                        "candidate_count": 0,
                    }
                )
                errors.append(
                    {
                        "packet_id": packet.get("packet_id"),
                        "lane_id": packet.get("lane_id"),
                        "stage": packet.get("stage"),
                        "message": str(exc),
                    }
                )
                continue

            packet_results.append(packet_result["packet"])
            for candidate in packet_result["candidates"]:
                lane_id = str(candidate.get("lane_id") or "").strip()
                if lane_added.get(lane_id, 0) >= max_per_lane:
                    continue
                dedupe_key = _candidate_dedupe_key(candidate)
                if not dedupe_key:
                    continue
                existing_index = candidate_keys.get(dedupe_key)
                if existing_index is None:
                    candidates.append(candidate)
                    candidate_keys[dedupe_key] = len(candidates) - 1
                    lane_added[lane_id] = lane_added.get(lane_id, 0) + 1
                    continue
                merged = _merge_candidate(candidates[existing_index], candidate)
                candidates[existing_index] = merged

    candidates.sort(key=lambda item: item.get("ranking_score") or 0, reverse=True)
    packet_results.sort(key=lambda item: _packet_sort_key(item))
    return {
        "candidates": candidates,
        "packet_results": packet_results,
        "errors": errors,
    }


def _execute_packet(
    packet: dict[str, Any],
    *,
    topic: str,
    anchor_terms: list[str],
    focus_terms: list[str],
    fetch_json: JsonFetcher,
    fetch_text: TextFetcher,
) -> dict[str, Any]:
    lane_id = str(packet.get("lane_id") or "").strip()
    queries = [str(item).strip() for item in (packet.get("queries") or []) if str(item).strip()]
    blacklist_terms = _clean_list(packet.get("blacklist_terms") or [])
    stage = str(packet.get("stage") or "seed").strip() or "seed"
    raw_candidates = _discover_lane(
        lane_id,
        queries,
        max_per_lane=max(len(queries), 1) * 2,
        fetch_json=fetch_json,
        fetch_text=fetch_text,
    )
    candidates: list[dict[str, Any]] = []
    for candidate in raw_candidates:
        candidate["packet_id"] = packet.get("packet_id")
        candidate["stage"] = stage
        candidate["track_id"] = str(packet.get("track_id") or "general").strip() or "general"
        candidate["track_label"] = str(packet.get("track_label") or "General").strip() or "General"
        candidate["blacklist_terms"] = blacklist_terms
        if _is_blacklisted_candidate(candidate, blacklist_terms=blacklist_terms):
            continue
        relevance_score, title_focus_overlap = _score_candidate_relevance(
            candidate,
            topic=topic,
            query=str(candidate.get("query") or ""),
            anchor_terms=anchor_terms,
            focus_terms=focus_terms,
        )
        if not _passes_relevance_threshold(score=relevance_score, stage=stage):
            continue
        candidate["relevance_score"] = relevance_score
        candidate["title_focus_overlap"] = title_focus_overlap
        candidate["relevance_band"] = _relevance_band(relevance_score)
        candidate["has_focus_terms"] = bool(focus_terms)
        candidate["discovery_stage"] = stage
        candidate["ranking_score"] = _ranking_score(candidate, lane_id=lane_id)
        if not _passes_ranking_threshold(candidate["ranking_score"], lane_id=lane_id):
            continue
        candidates.append(candidate)
    candidates.sort(key=lambda item: item.get("ranking_score") or 0, reverse=True)
    return {
        "packet": {
            "packet_id": packet.get("packet_id"),
            "lane_id": lane_id,
            "stage": stage,
            "priority": packet.get("priority"),
            "queries": queries,
            "candidate_count": len(candidates),
            "status": "completed",
        },
        "candidates": candidates,
    }


def _discover_lane(
    lane_id: str,
    queries: list[str],
    *,
    max_per_lane: int,
    fetch_json: JsonFetcher,
    fetch_text: TextFetcher,
) -> list[dict[str, Any]]:
    if lane_id == "primary_institutional":
        return _discover_institutional_web_search(lane_id, queries, max_per_lane=max_per_lane, fetch_text=fetch_text)
    if lane_id == "academic":
        return _discover_crossref(lane_id, queries, max_per_lane=max_per_lane, fetch_json=fetch_json)
    if lane_id == "literature":
        return _discover_openlibrary(lane_id, queries, max_per_lane=max_per_lane, fetch_json=fetch_json)
    if lane_id == "reference_web":
        return _discover_wikipedia(lane_id, queries, max_per_lane=max_per_lane, fetch_json=fetch_json)
    if lane_id == "reputable_media":
        return _discover_google_news_rss(lane_id, queries, max_per_lane=max_per_lane, fetch_text=fetch_text)
    if lane_id == "korean_news_rss":
        return _discover_korean_news_rss(lane_id, queries, max_per_lane=max_per_lane, fetch_text=fetch_text)
    return []


def _discover_institutional_web_search(
    lane_id: str,
    queries: list[str],
    *,
    max_per_lane: int,
    fetch_text: TextFetcher,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in queries:
        if len(candidates) >= max_per_lane:
            break
        endpoint = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        html = fetch_text(endpoint)
        for item in _parse_duckduckgo_results(html)[: max_per_lane * 2]:
            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or "").strip()
            dedupe_key = url or title
            if not dedupe_key or dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            source = {
                "label": title or url,
                "url": url,
                "kind": "institutional",
                "publisher": item.get("publisher") or _publisher_from_domain(url),
            }
            source.update(classify_source_record(source))
            if str(source.get("source_class") or "") not in {"institutional", "primary"}:
                continue
            candidates.append(
                {
                    "candidate_id": f"{lane_id}-{len(candidates)+1:03d}",
                    "lane_id": lane_id,
                    "query": query,
                    "title": title or url,
                    "url": url,
                    "publisher": source.get("publisher_resolved") or source.get("publisher") or item.get("publisher"),
                    "kind": "institutional",
                    "snippet": str(item.get("snippet") or "").strip(),
                    **{key: source.get(key) for key in ("source_class", "trust_tier", "trust_score", "domain", "tier_reason", "publisher_resolved")},
                }
            )
            if len(candidates) >= max_per_lane:
                break
    return candidates


def _discover_crossref(
    lane_id: str,
    queries: list[str],
    *,
    max_per_lane: int,
    fetch_json: JsonFetcher,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in queries:
        if len(candidates) >= max_per_lane:
            break
        for item in lane_tools.search_crossref(query, limit=max_per_lane, fetch_json_impl=fetch_json):
            if item.get("error"):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            key = url or title
            if not key or key in seen:
                continue
            seen.add(key)
            source = {
                "label": title or url,
                "url": url,
                "kind": "paper",
                "publisher": str(item.get("publisher") or "").strip(),
            }
            source.update(classify_source_record(source))
            candidates.append(
                {
                    "candidate_id": f"{lane_id}-{len(candidates)+1:03d}",
                    "lane_id": lane_id,
                    "query": query,
                    "title": title or url,
                    "url": url,
                    "publisher": source.get("publisher_resolved"),
                    "kind": "paper",
                    "published_at": str(item.get("published_at") or "").strip(),
                    "snippet": str(item.get("snippet") or "").strip(),
                    **{key: source.get(key) for key in ("source_class", "trust_tier", "trust_score", "domain", "tier_reason", "publisher_resolved")},
                }
            )
            if len(candidates) >= max_per_lane:
                break
    return candidates


def _discover_openlibrary(
    lane_id: str,
    queries: list[str],
    *,
    max_per_lane: int,
    fetch_json: JsonFetcher,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in queries:
        if len(candidates) >= max_per_lane:
            break
        literature_items = _fetch_literature_items(query, max_per_lane=max_per_lane, fetch_json=fetch_json)
        for item in literature_items:
            dedupe_key = str(item.get("url") or item.get("title") or "").strip()
            if not dedupe_key or dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            source = {
                "label": item.get("title") or item.get("url"),
                "url": item.get("url"),
                "kind": "book",
                "publisher": item.get("publisher"),
            }
            source.update(classify_source_record(source))
            candidates.append(
                {
                    "candidate_id": f"{lane_id}-{len(candidates)+1:03d}",
                    "lane_id": lane_id,
                    "query": query,
                    "title": item.get("title") or item.get("url"),
                    "url": item.get("url"),
                    "publisher": source.get("publisher_resolved"),
                    "kind": "book",
                    "author": item.get("author"),
                    "published_at": item.get("published_at"),
                    "snippet": item.get("snippet") or "",
                    **{key: source.get(key) for key in ("source_class", "trust_tier", "trust_score", "domain", "tier_reason", "publisher_resolved")},
                }
            )
            if len(candidates) >= max_per_lane:
                break
    return candidates


def _fetch_literature_items(query: str, *, max_per_lane: int, fetch_json: JsonFetcher) -> list[dict[str, Any]]:
    return [
        item
        for item in lane_tools.search_openlibrary(query, limit=max_per_lane, fetch_json_impl=fetch_json)
        if not item.get("error")
    ]


def _discover_wikipedia(
    lane_id: str,
    queries: list[str],
    *,
    max_per_lane: int,
    fetch_json: JsonFetcher,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in queries:
        if len(candidates) >= max_per_lane:
            break
        for item in lane_tools.search_wikipedia(query, limit=max_per_lane, fetch_json_impl=fetch_json):
            if item.get("error"):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            source = {
                "label": title or url,
                "url": url,
                "kind": "reference",
                "publisher": "Wikipedia",
            }
            source.update(classify_source_record(source))
            candidates.append(
                {
                    "candidate_id": f"{lane_id}-{len(candidates)+1:03d}",
                    "lane_id": lane_id,
                    "query": query,
                    "title": title or url,
                    "url": url,
                    "publisher": "Wikipedia",
                    "kind": "reference",
                    "snippet": str(item.get("snippet") or "").strip(),
                    "lang": str(item.get("lang") or "").strip(),
                    **{key: source.get(key) for key in ("source_class", "trust_tier", "trust_score", "domain", "tier_reason", "publisher_resolved")},
                }
            )
            if len(candidates) >= max_per_lane:
                break
    return candidates


def _discover_google_news_rss(
    lane_id: str,
    queries: list[str],
    *,
    max_per_lane: int,
    fetch_text: TextFetcher,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in queries:
        if len(candidates) >= max_per_lane:
            break
        for item in lane_tools.search_google_news_rss(query, limit=max_per_lane, fetch_text_impl=fetch_text):
            if item.get("error"):
                continue
            title = str(item.get("title") or "").strip()
            publisher = str(item.get("publisher") or "").strip()
            url = str(item.get("url") or "").strip()
            dedupe_key = url or title
            if not dedupe_key or dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            source = {
                "label": title or url,
                "url": url,
                "kind": "news",
                "publisher": publisher,
            }
            source.update(classify_source_record(source))
            candidates.append(
                {
                    "candidate_id": f"{lane_id}-{len(candidates)+1:03d}",
                    "lane_id": lane_id,
                    "query": query,
                    "title": title or url,
                    "url": url,
                    "publisher": source.get("publisher_resolved"),
                    "kind": "news",
                    "published_at": str(item.get("published_at") or "").strip(),
                    "snippet": str(item.get("snippet") or "").strip(),
                    "confidence": str(item.get("confidence") or "").strip(),
                    **{key: source.get(key) for key in ("source_class", "trust_tier", "trust_score", "domain", "tier_reason", "publisher_resolved")},
                }
            )
            if len(candidates) >= max_per_lane:
                break
    return candidates


def _discover_korean_news_rss(
    lane_id: str,
    queries: list[str],
    *,
    max_per_lane: int,
    fetch_text: TextFetcher,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in queries:
        if len(candidates) >= max_per_lane:
            break
        for item in lane_tools.search_korean_news_rss(query, limit=max_per_lane, fetch_text_impl=fetch_text):
            if item.get("error"):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            dedupe_key = url or title
            if not dedupe_key or dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            record = {
                "label": title or url,
                "url": url,
                "kind": "news",
                "publisher": str(item.get("publisher") or "").strip(),
            }
            record.update(classify_source_record(record))
            candidates.append(
                {
                    "candidate_id": f"{lane_id}-{len(candidates)+1:03d}",
                    "lane_id": lane_id,
                    "query": query,
                    "title": title or url,
                    "url": url,
                    "publisher": str(item.get("publisher") or "").strip(),
                    "kind": "news",
                    "published_at": str(item.get("published_at") or "").strip(),
                    "snippet": str(item.get("snippet") or "").strip(),
                    "confidence": str(item.get("confidence") or "").strip(),
                    **{key: record.get(key) for key in ("source_class", "trust_tier", "trust_score", "domain", "tier_reason", "publisher_resolved")},
                }
            )
            if len(candidates) >= max_per_lane:
                break
    return candidates


def _sort_packets(packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(packets, key=_packet_sort_key)


def _packet_sort_key(packet: dict[str, Any]) -> tuple[int, str, str]:
    priority = str(packet.get("priority") or "medium").strip().lower()
    try:
        priority_index = PACKET_PRIORITY_ORDER.index(priority)
    except ValueError:
        priority_index = len(PACKET_PRIORITY_ORDER)
    return (priority_index, str(packet.get("lane_id") or ""), str(packet.get("packet_id") or ""))


def _group_expansions_by_lane(query_expansions: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    seen: dict[str, set[str]] = {}
    for item in query_expansions:
        lane_id = str(item.get("target_lane") or "").strip()
        query = str(item.get("query") or "").strip()
        track_id = str(item.get("track_id") or "general").strip() or "general"
        track_label = str(item.get("track_label") or "General").strip() or "General"
        if not lane_id or not query:
            continue
        grouped.setdefault(lane_id, [])
        seen.setdefault(lane_id, set())
        key = f"{track_id}::{query}"
        if key in seen[lane_id]:
            continue
        seen[lane_id].add(key)
        grouped[lane_id].append(
            {
                "query": query,
                "track_id": track_id,
                "track_label": track_label,
            }
        )
    return grouped


def _count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _candidate_dedupe_key(candidate: dict[str, Any]) -> str:
    url = str(candidate.get("url") or "").strip()
    if url:
        return url.lower()
    title = str(candidate.get("title") or "").strip().lower()
    publisher = str(candidate.get("publisher") or "").strip().lower()
    return f"{title}::{publisher}".strip(":")


def _merge_candidate(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    current_score = float(existing.get("ranking_score") or 0.0)
    incoming_score = float(incoming.get("ranking_score") or 0.0)
    merged = dict(existing if current_score >= incoming_score else incoming)
    queries = [str(item).strip() for item in ([existing.get("query")] + [incoming.get("query")]) if str(item).strip()]
    deduped_queries: list[str] = []
    for query in queries:
        if query not in deduped_queries:
            deduped_queries.append(query)
    merged["query_history"] = deduped_queries
    return merged


def _lane_query_entries(lane: dict[str, Any]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    raw_entries = lane.get("query_entries") or []
    if raw_entries:
        for entry in raw_entries:
            query = str(entry.get("query") or "").strip()
            if not query:
                continue
            entries.append(
                {
                    "query": query,
                    "track_id": str(entry.get("track_id") or "general").strip() or "general",
                    "track_label": str(entry.get("track_label") or "General").strip() or "General",
                }
            )
        return entries
    for query in lane.get("queries") or []:
        query_text = str(query).strip()
        if not query_text:
            continue
        entries.append(
            {
                "query": query_text,
                "track_id": "general",
                "track_label": "General",
            }
        )
    return entries


def _build_query_expansions(topic: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expansions: list[dict[str, Any]] = []
    seen: set[str] = set()
    ranked_candidates = sorted(candidates, key=lambda item: item.get("ranking_score") or 0, reverse=True)
    for index, candidate in enumerate(ranked_candidates, start=1):
        title = str(candidate.get("title") or "").strip()
        publisher = str(candidate.get("publisher") or "").strip()
        lane_id = str(candidate.get("lane_id") or "").strip()
        query_specs = [
            (title, "source_title"),
            (" ".join(part for part in [title, topic] if part).strip(), "source_title_plus_topic"),
            (" ".join(part for part in [publisher, title] if part).strip(), "publisher_plus_title"),
        ]
        for query, reason in query_specs:
            normalized = " ".join(query.split()).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            expansions.append(
                {
                    "expansion_id": f"query-expansion-{index:03d}-{len(expansions)+1:03d}",
                    "query": normalized,
                    "source_candidate_id": candidate.get("candidate_id"),
                    "target_lane": lane_id,
                    "track_id": candidate.get("track_id") or "general",
                    "track_label": candidate.get("track_label") or "General",
                    "reason": reason,
                }
            )
    return expansions[:40]


def _build_source_note_seeds(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    query_map: dict[str, list[str]] = {}
    for item in _build_query_expansions("", candidates):
        candidate_id = str(item.get("source_candidate_id") or "").strip()
        query = str(item.get("query") or "").strip()
        if not candidate_id or not query:
            continue
        query_map.setdefault(candidate_id, [])
        if query not in query_map[candidate_id]:
            query_map[candidate_id].append(query)

    seeds: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "").strip()
        follow_up_queries = query_map.get(candidate_id, [])
        seeds.append(
            {
                "source_id": candidate_id,
                "title": candidate.get("title"),
                "source_url": candidate.get("url"),
                "publisher": candidate.get("publisher"),
                "kind": candidate.get("kind"),
                "source_class": candidate.get("source_class"),
                "trust_tier": candidate.get("trust_tier"),
                "domain": candidate.get("domain"),
                "lane_id": candidate.get("lane_id"),
                "discovery_confidence": candidate.get("confidence"),
                "discovered_via_query": candidate.get("query"),
                "discovery_stage": candidate.get("discovery_stage") or "seed",
                "track_id": candidate.get("track_id") or "general",
                "track_label": candidate.get("track_label") or "General",
                "relevance_score": candidate.get("relevance_score"),
                "relevance_band": candidate.get("relevance_band"),
                "ranking_score": candidate.get("ranking_score"),
                "follow_up_queries": follow_up_queries,
                "note_seed": "\n".join(
                    [
                        f"- title: {candidate.get('title') or 'n/a'}",
                        f"- url: {candidate.get('url') or 'n/a'}",
                        f"- publisher: {candidate.get('publisher') or 'n/a'}",
                        f"- lane: {candidate.get('lane_id') or 'n/a'}",
                        f"- discovery_stage: {candidate.get('discovery_stage') or 'seed'}",
                        f"- discovery_confidence: {candidate.get('confidence') or 'n/a'}",
                        f"- trust_tier: {candidate.get('trust_tier') or 'n/a'}",
                        f"- relevance_score: {candidate.get('relevance_score') or 'n/a'}",
                        f"- relevance_band: {candidate.get('relevance_band') or 'n/a'}",
                        f"- ranking_score: {candidate.get('ranking_score') or 'n/a'}",
                        f"- snippet: {candidate.get('snippet') or 'n/a'}",
                        f"- follow_up_queries: {', '.join(follow_up_queries) or 'n/a'}",
                    ]
                )
                + "\n",
            }
        )
    return seeds


def _discovery_summary(
    *,
    candidates: list[dict[str, Any]],
    packet_results: list[dict[str, Any]],
    query_expansions: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "candidate_count": len(candidates),
        "packet_count": len(packet_results),
        "query_expansion_count": len(query_expansions),
        "error_count": len(errors),
        "by_lane": _count_by(candidates, "lane_id"),
        "by_packet_lane": _count_by(packet_results, "lane_id"),
        "by_stage": _count_by(candidates, "discovery_stage"),
        "by_relevance_band": _count_by(candidates, "relevance_band"),
    }


def _score_candidate_relevance(
    candidate: dict[str, Any],
    *,
    topic: str,
    query: str,
    anchor_terms: list[str],
    focus_terms: list[str],
) -> tuple[float, float]:
    title_terms = set(_tokenize_for_relevance(str(candidate.get("title") or "")))
    context_terms = set(
        _tokenize_for_relevance(
            " ".join(
                [
                    str(candidate.get("snippet") or ""),
                    str(candidate.get("publisher") or ""),
                ]
            )
        )
    )
    candidate_terms = title_terms | context_terms
    if not candidate_terms:
        return 0.0, 0.0
    query_terms = set(_tokenize_for_relevance(query))
    topic_terms = set(_tokenize_for_relevance(topic))
    anchor_term_set = set(_tokenize_for_relevance(" ".join(anchor_terms)))
    focus_term_set = set(_tokenize_for_relevance(" ".join(focus_terms)))
    query_overlap = len(candidate_terms & query_terms) / max(len(query_terms), 1) if query_terms else 0.0
    topic_overlap = len(candidate_terms & topic_terms) / max(len(topic_terms), 1) if topic_terms else 0.0
    anchor_overlap = len(candidate_terms & anchor_term_set) / max(len(anchor_term_set), 1) if anchor_term_set else 0.0
    title_focus_overlap = len(title_terms & focus_term_set) / max(len(focus_term_set), 1) if focus_term_set else 0.0
    context_focus_overlap = len(context_terms & focus_term_set) / max(len(focus_term_set), 1) if focus_term_set else 0.0
    if focus_term_set:
        score = (
            (0.42 * anchor_overlap)
            + (0.2 * query_overlap)
            + (0.1 * topic_overlap)
            + (0.2 * title_focus_overlap)
            + (0.08 * context_focus_overlap)
        )
    else:
        score = (0.55 * anchor_overlap) + (0.3 * query_overlap) + (0.15 * topic_overlap)
    if candidate.get("source_class") in {"primary", "academic", "institutional", "literature"} and score > 0:
        score += 0.05
    return round(min(max(score, 0.0), 1.0), 3), round(min(max(title_focus_overlap, 0.0), 1.0), 3)


def _passes_relevance_threshold(*, score: float, stage: str) -> bool:
    threshold = 0.16 if stage == "expansion" else 0.1
    return score >= threshold


def _relevance_band(score: float) -> str:
    if score >= 0.5:
        return "high"
    if score >= 0.15:
        return "medium"
    if score > 0:
        return "low"
    return "off_topic"


def _tokenize_for_relevance(text: str) -> list[str]:
    stopwords = {
        "the", "and", "for", "with", "from", "into", "during", "about", "background",
        "news", "report", "study", "article", "paper", "book", "history", "historical",
        "대한", "에서", "으로", "하는", "연구", "자료", "기사", "보고서", "역사",
        "analysis", "overview", "chronology", "국경", "분쟁", "충돌", "배경", "연표", "개요",
    }
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]+|[가-힣]{2,}", str(text or "").lower())
    return [token for token in tokens if token not in stopwords]


def _is_blacklisted_candidate(candidate: dict[str, Any], *, blacklist_terms: list[str]) -> bool:
    if not blacklist_terms:
        return False
    haystack = " ".join(
        [
            str(candidate.get("title") or ""),
            str(candidate.get("snippet") or ""),
            str(candidate.get("publisher") or ""),
        ]
    ).lower()
    return any(term in haystack for term in blacklist_terms)


def _passes_ranking_threshold(score: float, *, lane_id: str) -> bool:
    thresholds = {
        "primary_institutional": 0.28,
        "academic": 0.24,
        "literature": 0.3,
        "reputable_media": 0.24,
        "reference_web": 0.2,
        "korean_news_rss": 0.22,
    }
    return score >= thresholds.get(lane_id, 0.18)


def _ranking_score(candidate: dict[str, Any], *, lane_id: str) -> float:
    relevance_score = float(candidate.get("relevance_score") or 0.0)
    trust_score = float(candidate.get("trust_score") or 0.0) / 4.0
    lane_fit = _lane_fit_bonus(candidate, lane_id=lane_id)
    publisher_bonus = _publisher_domain_bonus(candidate, lane_id=lane_id)
    penalty = _noise_penalty(candidate, lane_id=lane_id)
    title_focus_overlap = float(candidate.get("title_focus_overlap") or 0.0)
    confidence_bonus = _confidence_bonus(candidate, lane_id=lane_id)
    score = (
        (0.5 * relevance_score)
        + (0.2 * trust_score)
        + (0.15 * lane_fit)
        + (0.08 * title_focus_overlap)
        + publisher_bonus
        + confidence_bonus
        - penalty
    )
    return round(max(0.0, min(score, 1.0)), 3)


def _confidence_bonus(candidate: dict[str, Any], *, lane_id: str) -> float:
    if lane_id not in {"reputable_media", "korean_news_rss"}:
        return 0.0
    confidence = str(candidate.get("confidence") or "").strip().lower()
    if confidence == "high":
        return 0.04
    if confidence == "medium":
        return 0.0
    return -0.08


def _lane_fit_bonus(candidate: dict[str, Any], *, lane_id: str) -> float:
    source_class = str(candidate.get("source_class") or "")
    if lane_id == "primary_institutional":
        if source_class in {"primary", "institutional"}:
            return 1.0
        if source_class == "academic":
            return 0.4
        return 0.0
    if lane_id == "academic":
        if source_class == "academic":
            return 1.0
        if source_class in {"institutional", "primary"}:
            return 0.45
        return 0.0
    if lane_id == "literature":
        if source_class == "literature":
            return 1.0
        if source_class == "academic":
            return 0.55
        return 0.0
    if lane_id in {"reputable_media", "korean_news_rss"}:
        if source_class == "reputable_media":
            return 1.0
        if source_class in {"reference", "institutional"}:
            return 0.25
        return 0.0
    if lane_id == "reference_web":
        if source_class == "reference":
            return 1.0
        if source_class in {"institutional", "academic"}:
            return 0.35
        return 0.0
    return 0.25


def _publisher_domain_bonus(candidate: dict[str, Any], *, lane_id: str) -> float:
    publisher = str(candidate.get("publisher") or "").lower()
    domain = str(candidate.get("domain") or "").lower()
    title = str(candidate.get("title") or "").lower()
    if lane_id == "primary_institutional":
        return institutional_domain_bonus(domain)
    if lane_id == "literature":
        return literature_publisher_bonus(publisher, title)
    if lane_id in {"reputable_media", "korean_news_rss"}:
        return media_publisher_bonus(domain)
    if lane_id == "reference_web":
        return reference_domain_bonus(domain)
    return 0.0


def _noise_penalty(candidate: dict[str, Any], *, lane_id: str) -> float:
    haystack = " ".join(
        [
            str(candidate.get("title") or ""),
            str(candidate.get("snippet") or ""),
            str(candidate.get("publisher") or ""),
            str(candidate.get("domain") or ""),
        ]
    ).lower()
    if lane_id == "primary_institutional":
        return institutional_noise_penalty(haystack)
    if lane_id == "literature":
        return literature_noise_penalty(haystack)
    if lane_id in {"reputable_media", "korean_news_rss"}:
        return media_noise_penalty(haystack)
    if lane_id == "reference_web":
        return reference_noise_penalty(haystack)
    return 0.0


def _split_google_news_title(raw_title: str) -> tuple[str, str]:
    return lane_tools.split_google_news_title(raw_title)


def _wikipedia_languages_for_query(query: str) -> list[str]:
    return lane_tools.wikipedia_languages_for_query(query)


def _contains_korean(text: str) -> bool:
    return lane_tools.contains_korean(text)


def _parse_duckduckgo_results(html: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    pattern = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
        r'(?:<a[^>]+class="result__url"[^>]*>(?P<publisher>.*?)</a>).*?'
        r'(?:<a[^>]+class="result__snippet"[^>]*>|<div[^>]+class="result__snippet"[^>]*>)(?P<snippet>.*?)</(?:a|div)>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(html):
        url = _resolve_duckduckgo_href(match.group("href"))
        title = _clean_html_fragment(match.group("title"))
        publisher = _clean_html_fragment(match.group("publisher"))
        snippet = _clean_html_fragment(match.group("snippet"))
        if url or title:
            results.append(
                {
                    "url": url,
                    "title": title,
                    "publisher": publisher,
                    "snippet": snippet,
                }
            )
    return results


def _resolve_duckduckgo_href(href: str) -> str:
    raw = str(href or "").strip()
    if not raw:
        return ""
    if raw.startswith("//"):
        raw = f"https:{raw}"
    parsed = urlparse(raw)
    if "duckduckgo.com" in (parsed.netloc or "") and parsed.path.rstrip("/") == "/l":
        params = parse_qs(parsed.query)
        uddg = params.get("uddg")
        if uddg:
            return unquote(uddg[0])
    if raw.startswith("http"):
        return raw
    return raw


def _clean_html_fragment(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return " ".join(text.split()).strip()


def _publisher_from_domain(url: str) -> str:
    host = urlparse(str(url or "")).netloc.lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def _to_jsonl(records: list[dict[str, Any]]) -> str:
    if not records:
        return ""
    return "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n"


def _fetch_json(url: str) -> dict[str, Any]:  # pragma: no cover - live I/O
    return lane_tools.fetch_json(url)


def _fetch_text(url: str) -> str:  # pragma: no cover - live I/O
    return lane_tools.fetch_text(url)


def _clean_crossref_abstract(value: Any) -> str:
    return lane_tools.clean_crossref_abstract(value)


def _clean_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(str(value or "").split()).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return cleaned

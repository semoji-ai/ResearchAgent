from __future__ import annotations

import re
from typing import Any

from research_source_priors import lane_blacklist_terms


_GENERIC_TERMS = {
    "history",
    "historical",
    "overview",
    "chronology",
    "research",
    "study",
    "topic",
    "query",
    "history of",
    "역사",
    "개요",
    "연구",
    "조사",
    "주제",
}

_QUERY_FILLER_TERMS = {
    "what",
    "why",
    "how",
    "when",
    "where",
    "which",
    "does",
    "did",
    "is",
    "are",
    "was",
    "were",
    "대한",
    "관한",
    "어떻게",
    "무엇",
    "무엇인가",
    "왜",
    "언제",
    "어디",
    "어떤",
    "있는가",
}


def build_research_plan(
    *,
    topic: str,
    query: str,
    downstream_use: str = "",
    must_answer: list[str] | None = None,
    excluded_scope: list[str] | None = None,
    existing_sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_topic = str(topic or "").strip()
    normalized_query = str(query or "").strip()
    must_answer_items = _clean_list(must_answer)
    excluded_scope_items = _clean_list(excluded_scope)
    source_classes = sorted(
        {
            str(source.get("source_class") or "").strip()
            for source in (existing_sources or [])
            if str(source.get("source_class") or "").strip()
        }
    )
    anchor_terms = _collect_anchor_terms(normalized_topic, normalized_query, must_answer_items)
    focus_terms = anchor_terms[:8]
    query_topic = _build_query_seed_text(normalized_topic)
    query_question = _build_query_seed_text(normalized_query)
    base_queries = _base_query_entries(
        topic=normalized_topic,
        query=normalized_query,
        must_answer=must_answer_items,
    )
    use_korean_news_lane = _contains_korean(" ".join([normalized_topic, normalized_query, *must_answer_items]))

    lanes = [
        _lane(
            lane_id="primary_institutional",
            label="Primary / Institutional",
            preferred_classes=["primary", "institutional"],
            priority="highest",
            query_entries=_expand_lane_queries(
                base_queries,
                suffixes=[
                    "official history archive",
                    "museum archive document",
                    "official report chronology",
                    "institutional history",
                ],
            ),
        ),
        _lane(
            lane_id="academic",
            label="Academic",
            preferred_classes=["academic"],
            priority="highest",
            query_entries=_expand_lane_queries(
                base_queries,
                suffixes=[
                    "journal paper doi",
                    "site:nature.com",
                    "peer reviewed research",
                ],
            ),
        ),
        _lane(
            lane_id="literature",
            label="Literature / Reports",
            preferred_classes=["literature"],
            priority="high",
            query_entries=_expand_lane_queries(
                base_queries,
                suffixes=[
                    "book monograph report",
                    "site:books.google.com",
                    "long-form history",
                ],
            ),
        ),
        _lane(
            lane_id="reputable_media",
            label="Reputable Media",
            preferred_classes=["reputable_media"],
            priority="high",
            query_entries=_expand_lane_queries(
                base_queries,
                suffixes=[
                    "Reuters BBC AP background",
                    "analysis feature",
                ],
            ),
        ),
        _lane(
            lane_id="reference_web",
            label="Reference Web",
            preferred_classes=["reference", "web"],
            priority="medium",
            query_entries=_expand_lane_queries(
                base_queries,
                suffixes=[
                    "overview chronology",
                    "background summary",
                ],
            ),
        ),
    ]
    if use_korean_news_lane:
        lanes.append(
            _lane(
                lane_id="korean_news_rss",
                label="Korean News RSS",
                preferred_classes=["reputable_media", "web"],
                priority="high",
                query_entries=_expand_lane_queries(
                    base_queries,
                    suffixes=[
                        "연합뉴스",
                        "뉴스",
                    ],
                ),
            )
        )
    lanes.append(
        _lane(
            lane_id="image_evidence",
            label="Image Evidence",
            preferred_classes=["primary", "institutional", "academic", "reference"],
            priority="high",
            query_entries=_image_query_entries(normalized_topic, focus_terms),
        )
    )

    return {
        "version": "research-plan-v1",
        "topic": normalized_topic,
        "query": normalized_query,
        "query_topic": query_topic,
        "query_question": query_question,
        "downstream_use": str(downstream_use or "").strip(),
        "must_answer": must_answer_items,
        "excluded_scope": excluded_scope_items,
        "anchor_terms": anchor_terms,
        "focus_terms": focus_terms,
        "available_source_classes": source_classes,
        "lanes": lanes,
    }


def _lane(
    *,
    lane_id: str,
    label: str,
    preferred_classes: list[str],
    priority: str,
    query_entries: list[dict[str, str]],
) -> dict[str, Any]:
    effective_entries = query_entries[:8]
    return {
        "lane_id": lane_id,
        "label": label,
        "preferred_source_classes": preferred_classes,
        "priority": priority,
        "queries": [str(item.get("query") or "").strip() for item in effective_entries if str(item.get("query") or "").strip()],
        "query_entries": effective_entries,
        "blacklist_terms": lane_blacklist_terms(lane_id),
    }


def _base_query_entries(*, topic: str, query: str, must_answer: list[str]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for label, text in (
        ("Topic", topic),
        ("Primary Query", query),
    ):
        normalized = _build_query_seed_text(text)
        if normalized and normalized not in seen:
            seen.add(normalized)
            entries.append({"query": normalized, "track_id": "general", "track_label": label})
    for index, text in enumerate(must_answer, start=1):
        normalized = _build_query_seed_text(text)
        if normalized and normalized not in seen:
            seen.add(normalized)
            entries.append(
                {
                    "query": normalized,
                    "track_id": f"must_answer_{index:02d}",
                    "track_label": f"Must Answer {index}",
                }
            )
    return entries


def _expand_lane_queries(base_entries: list[dict[str, str]], *, suffixes: list[str]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in base_entries:
        query = str(entry.get("query") or "").strip()
        if not query:
            continue
        variants = [query]
        variants.extend(f"{query} {suffix}".strip() for suffix in suffixes[:2])
        for variant in variants:
            normalized = " ".join(variant.split()).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            entries.append(
                {
                    "query": normalized,
                    "track_id": str(entry.get("track_id") or "general").strip() or "general",
                    "track_label": str(entry.get("track_label") or "General").strip() or "General",
                }
            )
    return entries[:8]


def _image_query_entries(topic: str, focus_terms: list[str]) -> list[dict[str, str]]:
    seeds = [topic]
    if focus_terms:
        seeds.append(" ".join(focus_terms[:4]))
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, seed in enumerate(seeds, start=1):
        normalized_seed = _build_query_seed_text(seed)
        if not normalized_seed:
            continue
        for suffix in ("archive photo", "museum image", "historical photograph"):
            query = f"{normalized_seed} {suffix}".strip()
            if query in seen:
                continue
            seen.add(query)
            entries.append(
                {
                    "query": query,
                    "track_id": f"image_{index:02d}",
                    "track_label": f"Image {index}",
                }
            )
    return entries[:6]


def _collect_anchor_terms(topic: str, query: str, must_answer: list[str]) -> list[str]:
    seeds = [topic, query, *must_answer]
    tokens: list[str] = []
    seen: set[str] = set()
    for seed in seeds:
        for token in _tokenize(seed):
            if token in seen:
                continue
            seen.add(token)
            tokens.append(token)
            if len(tokens) >= 12:
                return tokens
    return tokens


def _build_query_seed_text(text: str) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    if not cleaned:
        return ""
    return cleaned


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]+|[가-힣]{2,}", str(text or "").lower())
    return [token for token in tokens if token not in _GENERIC_TERMS and token not in _QUERY_FILLER_TERMS]


def _contains_korean(text: str) -> bool:
    return any("\uac00" <= char <= "\ud7a3" for char in str(text or ""))


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

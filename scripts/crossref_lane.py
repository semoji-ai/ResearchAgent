#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

import research_lane_tools as lane_tools


def main() -> None:
    parser = argparse.ArgumentParser(
        description="학술 자료 검색 도구 — Crossref + Open Library + Google Books fallback",
    )
    parser.add_argument("query", help="검색어")
    parser.add_argument("--limit", type=int, default=5, help="소스당 최대 결과 수 (기본 5)")
    parser.add_argument("--papers-only", action="store_true", help="Crossref 논문만")
    parser.add_argument("--books-only", action="store_true", help="도서만 (Open Library + Google Books)")
    args = parser.parse_args()

    results = lane_tools.search_academic(
        args.query,
        limit=args.limit,
        papers_only=args.papers_only,
        books_only=args.books_only,
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

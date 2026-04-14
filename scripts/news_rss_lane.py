#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

import research_lane_tools as lane_tools


def main() -> None:
    parser = argparse.ArgumentParser(
        description="뉴스 RSS 수집 도구 — Google News + Korean RSS",
    )
    parser.add_argument("query", help="검색어 (한국어/영어 모두 가능)")
    parser.add_argument("--limit", type=int, default=8, help="소스당 최대 결과 수 (기본 8)")
    parser.add_argument("--ko-only", action="store_true", help="한국 뉴스만 수집")
    parser.add_argument("--en-only", action="store_true", help="영문 뉴스만 수집")
    args = parser.parse_args()

    results = lane_tools.search_news(
        args.query,
        limit=args.limit,
        ko_only=args.ko_only,
        en_only=args.en_only,
    )
    filtered = [item for item in results if item.get("confidence") != "blocked"]
    print(json.dumps(filtered, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

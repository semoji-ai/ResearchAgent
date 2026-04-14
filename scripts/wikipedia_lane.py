#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

import research_lane_tools as lane_tools


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wikipedia 검색 도구 — lane/rss/api 우선 수집용",
    )
    parser.add_argument("query", help="검색어 (한국어/영어 모두 가능)")
    parser.add_argument("--limit", type=int, default=5, help="최대 결과 수 (기본 5)")
    parser.add_argument("--content", action="store_true", help="첫 번째 결과의 본문 텍스트 포함")
    parser.add_argument("--char-limit", type=int, default=8000, help="본문 최대 글자 수 (기본 8000)")
    args = parser.parse_args()

    results = lane_tools.search_wikipedia(
        args.query,
        limit=args.limit,
        include_content=args.content,
        char_limit=args.char_limit,
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

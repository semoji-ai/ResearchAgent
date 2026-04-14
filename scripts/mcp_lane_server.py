#!/usr/bin/env python3
from __future__ import annotations

import json

import research_lane_tools as lane_tools

try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:  # pragma: no cover - optional runtime dependency
    raise SystemExit(
        "mcp.server.fastmcp is required to run scripts/mcp_lane_server.py. "
        f"Import failed: {exc}"
    ) from exc


mcp = FastMCP("researchagent-lane-tools")


@mcp.tool()
def wikipedia_search(query: str, limit: int = 5, content: bool = False, char_limit: int = 8000) -> str:
    results = lane_tools.search_wikipedia(
        query,
        limit=limit,
        include_content=content,
        char_limit=char_limit,
    )
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def news_search(query: str, limit: int = 10, ko_only: bool = False, en_only: bool = False) -> str:
    results = lane_tools.search_news(
        query,
        limit=limit,
        ko_only=ko_only,
        en_only=en_only,
    )
    filtered = [item for item in results if item.get("confidence") != "blocked"]
    return json.dumps(filtered, ensure_ascii=False, indent=2)


@mcp.tool()
def academic_search(query: str, limit: int = 5, papers_only: bool = False, books_only: bool = False) -> str:
    results = lane_tools.search_academic(
        query,
        limit=limit,
        papers_only=papers_only,
        books_only=books_only,
    )
    return json.dumps(results, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()

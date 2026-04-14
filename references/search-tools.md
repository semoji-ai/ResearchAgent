---
name: search-tools
description: ResearchAgent 검색 도구 사용 규칙 — lane/rss/api 우선, 일반 웹 검색은 fallback
---

# Search Tool Policy

## Priority

1. `scripts/wikipedia_lane.py`
2. `scripts/news_rss_lane.py`
3. `scripts/crossref_lane.py`
4. `scripts/research_launcher.py run-discovery`
5. 일반 WebSearch / WebFetch

lane 도구는 구조화된 결과를 바로 반환하고, `run-discovery`는 그 결과를 세션 번들과 source note seed로 저장합니다.

## Commands

### Wikipedia

```bash
python3 scripts/wikipedia_lane.py "query" --limit 5 --content
```

- `--content`: 첫 번째 결과의 Wikipedia 본문을 Jina Reader로 함께 가져옵니다.
- 배경, 역사, 인물, 연표 개요는 먼저 여기서 확인합니다.

### News RSS

```bash
python3 scripts/news_rss_lane.py "고유명사" --limit 10 --ko-only
python3 scripts/news_rss_lane.py "시장 키워드" --limit 10 --ko-only
python3 scripts/news_rss_lane.py "English keyword" --limit 10 --en-only
```

- 뉴스 쿼리는 좁은 키워드 2~3개로 분해합니다.
- `confidence=blocked` 후보는 자동 제외됩니다.
- 유사 제목은 자동 dedupe 됩니다.

### Academic / Books

```bash
python3 scripts/crossref_lane.py "query" --limit 5
python3 scripts/crossref_lane.py "query" --papers-only
python3 scripts/crossref_lane.py "query" --books-only
```

- 논문은 Crossref
- 도서는 Open Library 우선, 실패 시 Google Books fallback

### Session Discovery

```bash
python3 scripts/research_launcher.py prepare-session \
  --topic "Example Topic" \
  --root-dir "$HOME/research-wiki" \
  --query "example history and chronology" \
  --discover \
  --expansion-rounds 1
```

또는 기존 세션에 대해:

```bash
python3 scripts/research_launcher.py run-discovery \
  --topic "Example Topic" \
  --root-dir "$HOME/research-wiki" \
  --run-id "<run_id>" \
  --refresh-plan \
  --expansion-rounds 1
```

## MCP Exposure

MCP 도구가 필요한 경우:

```bash
python3 scripts/mcp_lane_server.py
```

노출 도구:

- `wikipedia_search`
- `news_search`
- `academic_search`

## Collection Caps

- Wikipedia: 1~5개
- News: 15개 이하 권장
- Academic / Books: 5개 권장
- Discovery lane candidate: lane당 기본 5개

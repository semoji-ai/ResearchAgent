from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import research_discovery as rd
import research_lane_tools as lane_tools
import research_launcher as rl


def _fake_fetch_json(url: str) -> dict:
    if "crossref" in url:
        return {
            "message": {
                "items": [
                    {
                        "title": ["Han frontier archaeology"],
                        "URL": "https://doi.org/10.1000/example",
                        "publisher": "Nature",
                        "created": {"date-parts": [[2024, 4, 10]]},
                        "abstract": "<jats:p>Archaeology evidence on the Han frontier.</jats:p>",
                    }
                ]
            }
        }
    if "openlibrary" in url:
        return {
            "docs": [
                {
                    "title": "Xiongnu and the Han Frontier",
                    "key": "/works/OL123W",
                    "publisher": ["Cambridge University Press"],
                    "author_name": ["Example Author"],
                    "first_publish_year": 2018,
                }
            ]
        }
    if "googleapis.com/books" in url:
        return {
            "items": [
                {
                    "volumeInfo": {
                        "title": "Xiongnu Frontier Book",
                        "infoLink": "https://books.google.com/books?id=fallback",
                        "publisher": "Oxford University Press",
                        "authors": ["Fallback Author"],
                        "publishedDate": "2019",
                    },
                    "searchInfo": {"textSnippet": "Fallback literature item."},
                }
            ]
        }
    if "wikipedia.org" in url:
        return {
            "query": {
                "search": [
                    {
                        "title": "Xiongnu",
                        "snippet": "Nomadic confederation in Inner Asia.",
                    },
                    {
                        "title": "Han–Xiongnu War",
                        "snippet": "Conflict between the Han dynasty and the Xiongnu.",
                    },
                ]
            }
        }
    raise AssertionError(f"Unexpected URL: {url}")


def _fake_fetch_text(url: str) -> str:
    if "duckduckgo.com/html" in url:
        return """
        <html><body>
          <div class="result">
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.archives.gov%2Fresearch%2Fmilitary%2Fww2">National Archives - World War II Military Records</a>
            <a class="result__url">www.archives.gov</a>
            <div class="result__snippet">Official archive materials and military records.</div>
          </div>
        </body></html>
        """
    if "news.google.com" in url:
        return """<?xml version="1.0" encoding="UTF-8"?><rss><channel>
          <item>
            <title>Han frontier tensions explained - Reuters</title>
            <link>https://news.google.com/articles/example</link>
            <pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate>
          </item>
        </channel></rss>"""
    if "news.naver.com/rss" in url:
        return """<?xml version="1.0" encoding="UTF-8"?><rss><channel>
          <item>
            <title>세종대왕 관련 기사</title>
            <link>https://news.naver.com/example</link>
            <description>세종대왕 연구 기사 요약.</description>
            <pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate>
          </item>
        </channel></rss>"""
    if "yna.co.kr/rss" in url:
        return """<?xml version="1.0" encoding="UTF-8"?><rss><channel></channel></rss>"""
    raise AssertionError(f"Unexpected URL: {url}")


def test_prepare_session_writes_research_plan(tmp_path):
    payload = rl.prepare_session(
        topic="우주 여행의 역사",
        query="우주 여행의 역사와 초기 경쟁 구도",
        run_id="run1",
        topic_slug="우주_여행의_역사",
        entity_slug="우주_여행",
        section_slug="역사",
        vault_dir=tmp_path,
        downstream_use="youtube-script",
        must_answer=["초기 경쟁 구도는 어떻게 형성됐나?"],
        excluded_scope=[],
        notes="",
        custom_assignments=[],
    )

    research_plan_path = Path(payload["research_plan_path"])
    assert research_plan_path.exists()
    plan = json.loads(research_plan_path.read_text(encoding="utf-8"))
    lane_ids = {item["lane_id"] for item in plan["lanes"]}
    assert {"primary_institutional", "academic", "literature", "reputable_media", "reference_web", "image_evidence"} <= lane_ids


def test_discover_source_candidates_builds_lane_results():
    plan = {
        "topic": "한나라와 흉노",
        "query": "국경 긴장은 어떻게 형성됐나?",
        "anchor_terms": ["한나라", "흉노"],
        "focus_terms": ["한나라", "흉노"],
        "lanes": [
            {"lane_id": "academic", "priority": "highest", "queries": ["한나라 흉노 archaeology"], "blacklist_terms": []},
            {"lane_id": "literature", "priority": "high", "queries": ["한나라 흉노 frontier book"], "blacklist_terms": []},
            {"lane_id": "reference_web", "priority": "medium", "queries": ["Xiongnu"], "blacklist_terms": []},
            {"lane_id": "reputable_media", "priority": "high", "queries": ["Han frontier Reuters"], "blacklist_terms": []},
        ],
    }
    result = rd.discover_source_candidates(plan, fetch_json=_fake_fetch_json, fetch_text=_fake_fetch_text)

    assert result["summary"]["candidate_count"] >= 3
    assert result["summary"]["by_lane"]["academic"] == 1
    assert result["summary"]["by_lane"]["reference_web"] >= 1
    assert "by_packet_lane" in result["summary"]
    assert result["source_note_seeds"]


def test_literature_lane_falls_back_to_google_books_when_openlibrary_fails():
    def fetch_with_openlibrary_failure(url: str) -> dict:
        if "openlibrary" in url:
            raise ConnectionError("openlibrary unavailable")
        return _fake_fetch_json(url)

    plan = {
        "topic": "한나라와 흉노",
        "query": "국경 긴장은 어떻게 형성됐나?",
        "anchor_terms": ["한나라", "흉노"],
        "focus_terms": ["한나라", "흉노"],
        "lanes": [
            {"lane_id": "literature", "priority": "high", "queries": ["Xiongnu frontier book"], "blacklist_terms": []},
        ],
    }
    result = rd.discover_source_candidates(plan, fetch_json=fetch_with_openlibrary_failure, fetch_text=_fake_fetch_text)

    assert result["summary"]["by_lane"]["literature"] == 1
    assert result["candidates"][0]["source_class"] == "literature"


def test_korean_news_rss_lane_parses_rss():
    plan = {
        "topic": "세종대왕",
        "query": "세종대왕의 업적은 무엇인가?",
        "anchor_terms": ["세종대왕"],
        "focus_terms": ["세종대왕"],
        "lanes": [
            {"lane_id": "korean_news_rss", "priority": "high", "queries": ["세종대왕"], "blacklist_terms": []},
        ],
    }
    result = rd.discover_source_candidates(plan, fetch_json=_fake_fetch_json, fetch_text=_fake_fetch_text)

    assert result["summary"]["by_lane"]["korean_news_rss"] == 1
    assert result["candidates"][0]["publisher"] == "Naver News"


def test_search_news_filters_blocked_and_dedupes_similar_titles():
    def fake_fetch_text(url: str) -> str:
        if "news.google.com" in url:
            return """<?xml version="1.0" encoding="UTF-8"?><rss><channel>
              <item>
                <title>AI chip boom reshapes supply chains - Reuters</title>
                <link>https://www.reuters.com/technology/ai-chip-boom</link>
                <pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate>
              </item>
              <item>
                <title>AI chip boom reshapes global supply chains - Reuters</title>
                <link>https://www.reuters.com/technology/ai-chip-boom-followup</link>
                <pubDate>Tue, 02 Jan 2024 00:05:00 GMT</pubDate>
              </item>
              <item>
                <title>AI chip boom recap - Some Blog</title>
                <link>https://blog.naver.com/some-post</link>
                <pubDate>Tue, 02 Jan 2024 00:10:00 GMT</pubDate>
              </item>
            </channel></rss>"""
        if "news.naver.com/rss" in url:
            return """<?xml version="1.0" encoding="UTF-8"?><rss><channel></channel></rss>"""
        if "yna.co.kr/rss" in url:
            return """<?xml version="1.0" encoding="UTF-8"?><rss><channel></channel></rss>"""
        raise AssertionError(f"Unexpected URL: {url}")

    results = lane_tools.search_news("AI chip boom", limit=5, fetch_text_impl=fake_fetch_text)

    assert len([item for item in results if not item.get("error")]) == 1
    assert results[0]["publisher"] == "Reuters"
    assert results[0]["confidence"] == "high"


def test_search_wikipedia_can_include_content():
    def fake_fetch_json(url: str) -> dict:
        assert "wikipedia.org" in url
        return {
            "query": {
                "search": [
                    {
                        "title": "Steam engine",
                        "snippet": "A heat engine performing mechanical work.",
                    }
                ]
            }
        }

    def fake_fetch_text(url: str) -> str:
        assert url.startswith("https://r.jina.ai/")
        return "Steam engine full article body"

    results = lane_tools.search_wikipedia(
        "Steam engine",
        limit=3,
        include_content=True,
        fetch_json_impl=fake_fetch_json,
        fetch_text_impl=fake_fetch_text,
    )

    assert results[0]["title"] == "Steam engine"
    assert results[0]["content"] == "Steam engine full article body"


def test_search_academic_respects_books_only_and_papers_only():
    books_only = lane_tools.search_academic(
        "Xiongnu frontier",
        limit=5,
        books_only=True,
        fetch_json_impl=_fake_fetch_json,
    )
    papers_only = lane_tools.search_academic(
        "Xiongnu frontier",
        limit=5,
        papers_only=True,
        fetch_json_impl=_fake_fetch_json,
    )

    assert books_only
    assert all(item.get("kind") == "book" for item in books_only)
    assert papers_only
    assert all(item.get("kind") == "paper" for item in papers_only)

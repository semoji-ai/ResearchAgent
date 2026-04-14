from __future__ import annotations

import json
import re
from typing import Any, Callable
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


JsonFetcher = Callable[[str], dict[str, Any]]
TextFetcher = Callable[[str], str]

USER_AGENT = "ResearchAgent/0.3"
JINA_READER_PREFIX = "https://r.jina.ai/"

TRUSTED_NEWS_DOMAINS: frozenset[str] = frozenset(
    {
        "yna.co.kr",
        "yonhapnews.co.kr",
        "chosun.com",
        "joongang.co.kr",
        "donga.com",
        "hani.co.kr",
        "hankookilbo.com",
        "mk.co.kr",
        "hankyung.com",
        "sedaily.com",
        "etnews.com",
        "zdnet.co.kr",
        "itchosun.com",
        "newsis.com",
        "newspim.com",
        "news1.kr",
        "ytn.co.kr",
        "sbs.co.kr",
        "kbs.co.kr",
        "mbc.co.kr",
        "reuters.com",
        "apnews.com",
        "bbc.com",
        "bbc.co.uk",
        "nytimes.com",
        "wsj.com",
        "ft.com",
        "economist.com",
        "bloomberg.com",
        "techcrunch.com",
        "wired.com",
        "theguardian.com",
        "washingtonpost.com",
        "cnn.com",
        "nbcnews.com",
        "forbes.com",
        "nature.com",
        "science.org",
        "ncbi.nlm.nih.gov",
        "who.int",
    }
)

TRUSTED_NEWS_PUBLISHERS: frozenset[str] = frozenset(
    {
        "연합뉴스",
        "yonhap",
        "yonhap news",
        "reuters",
        "associated press",
        "ap",
        "bbc",
        "the new york times",
        "new york times",
        "wall street journal",
        "financial times",
        "the economist",
        "bloomberg",
        "the washington post",
        "washington post",
        "the guardian",
        "cnn",
        "nbc news",
        "forbes",
        "ytn",
        "kbs",
        "mbc",
        "sbs",
        "newsis",
        "news1",
        "joongang ilbo",
        "chosun ilbo",
        "dong-a ilbo",
        "hankyung",
        "maeil business",
    }
)

BLOCKED_PATTERNS: tuple[str, ...] = (
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "blog.naver.com",
    "naver.com/blog",
    "tistory.com",
    "wordpress.com",
    "blogspot.com",
    "cafe.naver.com",
    "cafe.daum.net",
)

KOREAN_NEWS_RSS_SOURCES = [
    {
        "name": "naver_news",
        "publisher": "Naver News",
        "url_template": "https://news.naver.com/rss/search.naver?query={query}",
    },
    {
        "name": "yonhap",
        "publisher": "연합뉴스",
        "url_template": "https://www.yna.co.kr/rss/search.nhn?query={query}",
    },
]


def fetch_json(url: str) -> dict[str, Any]:  # pragma: no cover - live I/O
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str) -> str:  # pragma: no cover - live I/O
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


def contains_korean(text: str) -> bool:
    return any("\uac00" <= char <= "\ud7a3" for char in str(text or ""))


def wikipedia_languages_for_query(query: str) -> list[str]:
    return ["ko", "en"] if contains_korean(query) else ["en", "ko"]


def extract_domain(url: str) -> str:
    try:
        host = urlparse(str(url or "")).netloc.lower().strip()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def news_confidence(url: str, *, publisher: str = "") -> str:
    domain = extract_domain(url)
    url_lower = str(url or "").lower()
    publisher_lower = str(publisher or "").strip().lower()
    for blocked in BLOCKED_PATTERNS:
        if blocked in domain or blocked in url_lower:
            return "blocked"
    for trusted in TRUSTED_NEWS_DOMAINS:
        if domain == trusted or domain.endswith("." + trusted):
            return "high"
    if publisher_lower and publisher_lower in TRUSTED_NEWS_PUBLISHERS:
        return "high"
    return "medium"


def title_similar(first: str, second: str, threshold: float = 0.75) -> bool:
    words1 = set(re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]+|[가-힣]{2,}", str(first or "").lower()))
    words2 = set(re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]+|[가-힣]{2,}", str(second or "").lower()))
    if len(words1) < 3 or len(words2) < 3:
        return False
    overlap = len(words1 & words2)
    return overlap / min(len(words1), len(words2)) >= threshold


def split_google_news_title(raw_title: str) -> tuple[str, str]:
    title = str(raw_title or "").strip()
    if " - " not in title:
        return title, ""
    parts = [part.strip() for part in title.rsplit(" - ", 1)]
    if len(parts) != 2:
        return title, ""
    return parts[0], parts[1]


def clean_crossref_abstract(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return " ".join(cleaned.split()).strip()[:400]


def clean_html_fragment(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return " ".join(text.split()).strip()


def search_wikipedia(
    query: str,
    *,
    limit: int = 5,
    include_content: bool = False,
    char_limit: int = 8000,
    fetch_json_impl: JsonFetcher | None = None,
    fetch_text_impl: TextFetcher | None = None,
) -> list[dict[str, Any]]:
    json_fetcher = fetch_json_impl or fetch_json
    text_fetcher = fetch_text_impl or fetch_text
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for lang in wikipedia_languages_for_query(query):
        if len(results) >= limit:
            break
        endpoint = (
            f"https://{lang}.wikipedia.org/w/api.php"
            f"?action=query&list=search&srsearch={quote_plus(query)}"
            f"&srlimit={limit}&format=json&utf8=1"
        )
        try:
            payload = json_fetcher(endpoint)
        except Exception as exc:
            results.append({"error": str(exc), "lang": lang, "query": query})
            continue
        for item in (payload.get("query") or {}).get("search") or []:
            title = str(item.get("title") or "").strip()
            url = f"https://{lang}.wikipedia.org/wiki/{quote_plus(title.replace(' ', '_'))}" if title else ""
            if not url or url in seen:
                continue
            seen.add(url)
            results.append(
                {
                    "title": title,
                    "url": url,
                    "lang": lang,
                    "snippet": clean_html_fragment(str(item.get("snippet") or "")),
                    "publisher": "Wikipedia",
                    "kind": "reference",
                }
            )
            if len(results) >= limit:
                break

    if include_content and results and not results[0].get("error"):
        top_url = str(results[0].get("url") or "").strip()
        if top_url:
            results[0]["content"] = fetch_wikipedia_article_content(
                top_url,
                char_limit=char_limit,
                fetch_text_impl=text_fetcher,
            )
    return results


def fetch_wikipedia_article_content(
    url: str,
    *,
    char_limit: int = 8000,
    fetch_text_impl: TextFetcher | None = None,
) -> str:
    text_fetcher = fetch_text_impl or fetch_text
    jina_url = JINA_READER_PREFIX + str(url or "").strip()
    try:
        return text_fetcher(jina_url)[:char_limit]
    except Exception as exc:
        return f"[content fetch failed: {exc}]"


def search_google_news_rss(
    query: str,
    *,
    limit: int = 8,
    fetch_text_impl: TextFetcher | None = None,
) -> list[dict[str, Any]]:
    text_fetcher = fetch_text_impl or fetch_text
    endpoint = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    )
    results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []
    try:
        xml_text = text_fetcher(endpoint)
        root = ET.fromstring(xml_text)
    except Exception as exc:
        return [{"error": str(exc), "source": "google_news_rss", "query": query}]

    for item in root.findall(".//item"):
        if len(results) >= limit:
            break
        raw_title = (item.findtext("title") or "").strip()
        title, publisher = split_google_news_title(raw_title)
        url = (item.findtext("link") or "").strip()
        confidence = news_confidence(url, publisher=publisher)
        if confidence == "blocked":
            continue
        dedupe_key = url or title
        if not dedupe_key or dedupe_key in seen_urls:
            continue
        if any(title_similar(title, previous) for previous in seen_titles):
            continue
        seen_urls.add(dedupe_key)
        seen_titles.append(title)
        results.append(
            {
                "title": title,
                "url": url,
                "published_at": (item.findtext("pubDate") or "").strip(),
                "publisher": publisher,
                "confidence": confidence,
                "kind": "news",
                "source": "google_news_rss",
                "query": query,
            }
        )
    return results


def search_korean_news_rss(
    query: str,
    *,
    limit: int = 8,
    fetch_text_impl: TextFetcher | None = None,
) -> list[dict[str, Any]]:
    text_fetcher = fetch_text_impl or fetch_text
    results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []

    for source in KOREAN_NEWS_RSS_SOURCES:
        if len(results) >= limit:
            break
        endpoint = source["url_template"].format(query=quote_plus(query))
        try:
            xml_text = text_fetcher(endpoint)
            root = ET.fromstring(xml_text)
        except Exception as exc:
            results.append({"error": str(exc), "source": source["name"], "query": query})
            continue
        for item in root.findall(".//item"):
            if len(results) >= limit:
                break
            title = (item.findtext("title") or "").strip()
            url = (item.findtext("link") or "").strip()
            confidence = news_confidence(url, publisher=source["publisher"])
            if confidence == "blocked":
                continue
            dedupe_key = url or title
            if not dedupe_key or dedupe_key in seen_urls:
                continue
            if any(title_similar(title, previous) for previous in seen_titles):
                continue
            seen_urls.add(dedupe_key)
            seen_titles.append(title)
            results.append(
                {
                    "title": title,
                    "url": url,
                    "published_at": (item.findtext("pubDate") or "").strip(),
                    "snippet": (item.findtext("description") or "").strip()[:200],
                    "publisher": source["publisher"],
                    "confidence": confidence,
                    "kind": "news",
                    "source": source["name"],
                    "query": query,
                }
            )
    return results


def search_news(
    query: str,
    *,
    limit: int = 8,
    ko_only: bool = False,
    en_only: bool = False,
    fetch_text_impl: TextFetcher | None = None,
) -> list[dict[str, Any]]:
    text_fetcher = fetch_text_impl or fetch_text
    results: list[dict[str, Any]] = []
    if not ko_only:
        results.extend(search_google_news_rss(query, limit=limit, fetch_text_impl=text_fetcher))
    if not en_only:
        results.extend(search_korean_news_rss(query, limit=limit, fetch_text_impl=text_fetcher))

    deduped: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    seen_titles: list[str] = []
    for item in results:
        if item.get("error"):
            deduped.append(item)
            continue
        title = str(item.get("title") or "").strip()
        key = str(item.get("url") or title).strip()
        if not key or key in seen_keys:
            continue
        if any(title_similar(title, previous) for previous in seen_titles):
            continue
        seen_keys.add(key)
        seen_titles.append(title)
        deduped.append(item)
    return deduped[: limit * 2]


def search_crossref(
    query: str,
    *,
    limit: int = 5,
    fetch_json_impl: JsonFetcher | None = None,
) -> list[dict[str, Any]]:
    json_fetcher = fetch_json_impl or fetch_json
    endpoint = f"https://api.crossref.org/works?query={quote_plus(query)}&rows={limit}"
    try:
        payload = json_fetcher(endpoint)
    except Exception as exc:
        return [{"error": str(exc), "source": "crossref", "query": query}]

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in (payload.get("message") or {}).get("items") or []:
        title = " ".join(item.get("title") or []).strip()
        url = str(item.get("URL") or "").strip()
        key = url or title
        if not key or key in seen:
            continue
        seen.add(key)
        date_parts = ((item.get("created") or {}).get("date-parts") or [[]])[0]
        results.append(
            {
                "title": title,
                "url": url,
                "doi": str(item.get("DOI") or "").strip(),
                "author": ", ".join(
                    f"{author.get('given', '')} {author.get('family', '')}".strip()
                    for author in (item.get("author") or [])[:3]
                ),
                "publisher": str(item.get("publisher") or "").strip(),
                "published_at": "-".join(str(part) for part in date_parts if part),
                "snippet": clean_crossref_abstract(item.get("abstract")),
                "kind": "paper",
                "source": "crossref",
                "query": query,
            }
        )
        if len(results) >= limit:
            break
    return results


def search_openlibrary(
    query: str,
    *,
    limit: int = 5,
    fetch_json_impl: JsonFetcher | None = None,
) -> list[dict[str, Any]]:
    json_fetcher = fetch_json_impl or fetch_json
    endpoint = f"https://openlibrary.org/search.json?q={quote_plus(query)}&limit={limit}"
    try:
        payload = json_fetcher(endpoint)
        docs = payload.get("docs") or []
        if docs:
            return [
                {
                    "title": str(item.get("title") or "").strip(),
                    "url": f"https://openlibrary.org{item['key']}" if item.get("key") else "",
                    "author": ", ".join((item.get("author_name") or [])[:2]),
                    "publisher": ", ".join((item.get("publisher") or [])[:2])[:120],
                    "published_at": str(item.get("first_publish_year") or ""),
                    "snippet": "",
                    "kind": "book",
                    "source": "openlibrary",
                    "query": query,
                }
                for item in docs[:limit]
            ]
    except Exception:
        pass

    endpoint = f"https://www.googleapis.com/books/v1/volumes?q={quote_plus(query)}&maxResults={limit}"
    try:
        payload = json_fetcher(endpoint)
    except Exception as exc:
        return [{"error": str(exc), "source": "openlibrary+google_books", "query": query}]
    results: list[dict[str, Any]] = []
    for item in (payload.get("items") or [])[:limit]:
        info = item.get("volumeInfo") or {}
        results.append(
            {
                "title": str(info.get("title") or "").strip(),
                "url": str(info.get("infoLink") or "").strip(),
                "author": ", ".join((info.get("authors") or [])[:2]),
                "publisher": str(info.get("publisher") or "").strip(),
                "published_at": str(info.get("publishedDate") or "").strip(),
                "snippet": str((item.get("searchInfo") or {}).get("textSnippet") or info.get("description") or "").strip()[:300],
                "kind": "book",
                "source": "google_books",
                "query": query,
            }
        )
    return results


def search_academic(
    query: str,
    *,
    limit: int = 5,
    papers_only: bool = False,
    books_only: bool = False,
    fetch_json_impl: JsonFetcher | None = None,
) -> list[dict[str, Any]]:
    json_fetcher = fetch_json_impl or fetch_json
    results: list[dict[str, Any]] = []
    if not books_only:
        results.extend(search_crossref(query, limit=limit, fetch_json_impl=json_fetcher))
    if not papers_only:
        results.extend(search_openlibrary(query, limit=limit, fetch_json_impl=json_fetcher))
    return results

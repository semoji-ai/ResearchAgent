from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


_PRIMARY_HINTS = {
    "primary",
    "archive",
    "archival",
    "museum",
    "document",
}

_ACADEMIC_HINTS = {
    "paper",
    "journal",
}

_LITERATURE_HINTS = {
    "book",
    "literature",
    "monograph",
    "report",
}

_REPUTABLE_MEDIA_DOMAINS = {
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "nytimes.com",
    "ft.com",
    "wsj.com",
    "bloomberg.com",
    "economist.com",
    "washingtonpost.com",
    "theguardian.com",
    "npr.org",
    "cnn.com",
    "nbcnews.com",
    "forbes.com",
    "yna.co.kr",
    "yonhapnews.co.kr",
    "newsis.com",
    "news1.kr",
    "mk.co.kr",
    "hankyung.com",
    "sedaily.com",
    "chosun.com",
    "joongang.co.kr",
    "donga.com",
    "hani.co.kr",
    "hankookilbo.com",
    "ytn.co.kr",
    "sbs.co.kr",
    "kbs.co.kr",
    "mbc.co.kr",
    "etnews.com",
    "zdnet.co.kr",
    "techcrunch.com",
    "wired.com",
}

_REPUTABLE_MEDIA_PUBLISHERS = {
    "reuters",
    "associated press",
    "ap",
    "bbc",
    "the new york times",
    "new york times",
    "financial times",
    "wall street journal",
    "bloomberg",
    "the economist",
    "washington post",
    "the guardian",
    "npr",
    "cnn",
    "nbc news",
    "forbes",
    "연합뉴스",
    "yonhap",
    "yonhap news",
    "newsis",
    "news1",
    "maeil business",
    "hankyung",
    "chosun ilbo",
    "joongang ilbo",
    "dong-a ilbo",
    "ytn",
    "kbs",
    "mbc",
    "sbs",
}

_REFERENCE_DOMAINS = {
    "wikipedia.org",
    "britannica.com",
}

_INSTITUTIONAL_DOMAINS = {
    "archives.gov",
    "nara.gov",
    "history.army.mil",
    "army.mil",
    "navy.mil",
    "af.mil",
    "marines.mil",
    "iwm.org.uk",
    "nationalww2museum.org",
    "loc.gov",
}


def classify_source_record(source: dict[str, Any]) -> dict[str, Any]:
    kind = str(source.get("kind") or "").strip().lower()
    url = str(source.get("url") or "").strip()
    domain = _extract_domain(url)
    publisher = str(source.get("publisher") or "").strip()
    label = str(source.get("label") or "").strip()

    if kind in _PRIMARY_HINTS:
        source_class = "primary"
        trust_tier = "highest"
        reason = f"kind={kind or 'primary'}"
    elif kind in _ACADEMIC_HINTS:
        source_class = "academic"
        trust_tier = "highest"
        reason = f"kind={kind or 'academic'}"
    elif kind in _LITERATURE_HINTS:
        source_class = "literature"
        trust_tier = "high"
        reason = f"kind={kind or 'literature'}"
    elif _is_academic_domain(domain):
        source_class = "academic"
        trust_tier = "highest"
        reason = f"academic_domain={domain or 'n/a'}"
    elif _is_institutional_domain(domain):
        source_class = "institutional"
        trust_tier = "high"
        reason = f"institutional_domain={domain or 'n/a'}"
    elif _is_reputable_media_publisher(publisher):
        source_class = "reputable_media"
        trust_tier = "high"
        reason = f"reputable_media_publisher={publisher or 'n/a'}"
    elif _is_reputable_media_domain(domain):
        source_class = "reputable_media"
        trust_tier = "high"
        reason = f"reputable_media_domain={domain or 'n/a'}"
    elif _is_official_org_source(label=label, url=url, domain=domain, publisher=publisher):
        source_class = "institutional"
        trust_tier = "high"
        reason = f"official_org_source={domain or publisher or 'n/a'}"
    elif _is_reference_domain(domain):
        source_class = "reference"
        trust_tier = "medium"
        reason = f"reference_domain={domain or 'n/a'}"
    elif domain:
        source_class = "web"
        trust_tier = "medium"
        reason = f"generic_domain={domain}"
    else:
        source_class = "hint"
        trust_tier = "low"
        reason = "no_url_or_domain"

    return {
        "source_class": source_class,
        "trust_tier": trust_tier,
        "trust_score": _trust_score(trust_tier),
        "domain": domain,
        "publisher_resolved": publisher or domain,
        "tier_reason": reason,
    }


def _extract_domain(url: str) -> str:
    if not url:
        return ""
    host = urlparse(url).netloc.lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def _is_academic_domain(domain: str) -> bool:
    return bool(domain) and (
        domain.endswith(".edu")
        or domain.endswith(".ac.kr")
        or domain.endswith(".edu.cn")
        or domain.endswith(".ac.uk")
        or domain.startswith("doi.org")
        or domain.endswith("springer.com")
        or domain.endswith("nature.com")
        or domain.endswith("sciencedirect.com")
        or domain.endswith("jstor.org")
    )


def _is_institutional_domain(domain: str) -> bool:
    return bool(domain) and (
        any(domain == item or domain.endswith(f".{item}") for item in _INSTITUTIONAL_DOMAINS)
        or domain.endswith(".mil")
        or domain.endswith(".gov")
        or domain.endswith(".go.kr")
        or domain.endswith(".gov.uk")
        or domain.endswith(".museum")
        or "museum" in domain
        or domain.endswith(".or.kr")
    )


def _is_reputable_media_domain(domain: str) -> bool:
    return any(domain == item or domain.endswith(f".{item}") for item in _REPUTABLE_MEDIA_DOMAINS)


def _is_reputable_media_publisher(publisher: str) -> bool:
    normalized = str(publisher or "").strip().lower()
    return normalized in _REPUTABLE_MEDIA_PUBLISHERS


def _is_reference_domain(domain: str) -> bool:
    return any(domain == item or domain.endswith(f".{item}") for item in _REFERENCE_DOMAINS)


def _is_official_org_source(*, label: str, url: str, domain: str, publisher: str) -> bool:
    if not domain or not publisher:
        return False
    if _is_reputable_media_domain(domain) or _is_reference_domain(domain) or _is_academic_domain(domain):
        return False
    text = " ".join([str(label or "").lower(), str(url or "").lower(), str(publisher or "").lower()])
    return any(
        marker in text
        for marker in (
            "official history",
            "company history",
            "/about-us/history",
            "/company/history",
            "our history",
            "history of",
        )
    )


def _trust_score(tier: str) -> int:
    return {
        "highest": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
        "unverified": 0,
    }.get(str(tier or "").strip().lower(), 0)

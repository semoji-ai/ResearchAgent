from __future__ import annotations


COMMON_BLACKLIST_TERMS = [
    "k-drama",
    "drama",
    "movie",
    "film",
    "actor",
    "artist",
    "racing",
    "celebrity",
    "fashion",
    "music",
    "playlist",
    "trailer",
]

INSTITUTIONAL_BLACKLIST_TERMS = [
    "tickets",
    "ticket",
    "visit",
    "visitor",
    "opening hours",
    "hours",
    "shop",
    "gift shop",
    "donate",
    "membership",
    "event calendar",
]

LITERATURE_BLACKLIST_TERMS = [
    "novel",
    "poetry",
    "fiction",
    "거침없는",
    "쉽게 읽는",
    "만화",
    "한 권으로",
    "스토리",
    "story of",
    "for beginners",
    "play.google.com",
    "books.google",
    "google books",
    "교보문고",
    "yes24",
    "알라딘",
]

REPUTABLE_MEDIA_BLACKLIST_TERMS = [
    "box office",
    "tv series",
    "album",
    "concert",
    "lifestyle",
    "entertainment",
    "celebrity",
]

REFERENCE_BLACKLIST_TERMS = [
    "disambiguation",
    "fandom",
    "game wiki",
]

TRUSTED_LITERATURE_PUBLISHERS = (
    "cambridge university press",
    "oxford university press",
    "harvard university press",
    "princeton university press",
    "yale university press",
    "routledge",
    "springer",
    "brill",
    "university press",
)

TRUSTED_MEDIA_HOST_TOKENS = (
    "reuters.com",
    "bbc.com",
    "bbc.co.uk",
    "apnews.com",
    "ft.com",
    "economist.com",
    "nytimes.com",
    "bloomberg.com",
    "wsj.com",
    "washingtonpost.com",
    "theguardian.com",
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
)

TRUSTED_REFERENCE_HOST_TOKENS = (
    "wikipedia.org",
    "britannica.com",
)

TRUSTED_INSTITUTIONAL_HOST_TOKENS = (
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
    ".gov",
    ".mil",
    ".museum",
)


def lane_blacklist_terms(lane_id: str) -> list[str]:
    if lane_id == "primary_institutional":
        return COMMON_BLACKLIST_TERMS + INSTITUTIONAL_BLACKLIST_TERMS
    if lane_id == "reputable_media":
        return COMMON_BLACKLIST_TERMS + REPUTABLE_MEDIA_BLACKLIST_TERMS
    if lane_id == "literature":
        return COMMON_BLACKLIST_TERMS + LITERATURE_BLACKLIST_TERMS
    if lane_id == "reference_web":
        return REFERENCE_BLACKLIST_TERMS
    return COMMON_BLACKLIST_TERMS


def literature_publisher_bonus(publisher: str, title: str) -> float:
    haystack = " ".join([publisher or "", title or ""]).lower()
    return 0.12 if any(item in haystack for item in TRUSTED_LITERATURE_PUBLISHERS) else 0.0


def media_publisher_bonus(domain: str) -> float:
    return 0.1 if any(item in (domain or "").lower() for item in TRUSTED_MEDIA_HOST_TOKENS) else 0.0


def institutional_domain_bonus(domain: str) -> float:
    return 0.14 if any(item in (domain or "").lower() for item in TRUSTED_INSTITUTIONAL_HOST_TOKENS) else 0.0


def reference_domain_bonus(domain: str) -> float:
    return 0.08 if any(item in (domain or "").lower() for item in TRUSTED_REFERENCE_HOST_TOKENS) else 0.0


def literature_noise_penalty(haystack: str) -> float:
    return 0.22 if any(item in (haystack or "").lower() for item in LITERATURE_BLACKLIST_TERMS) else 0.0


def media_noise_penalty(haystack: str) -> float:
    return 0.18 if any(item in (haystack or "").lower() for item in ("opinion", "review", "lifestyle", "entertainment", "celebrity")) else 0.0


def institutional_noise_penalty(haystack: str) -> float:
    return 0.22 if any(item in (haystack or "").lower() for item in INSTITUTIONAL_BLACKLIST_TERMS) else 0.0


def reference_noise_penalty(haystack: str) -> float:
    return 0.3 if any(item in (haystack or "").lower() for item in REFERENCE_BLACKLIST_TERMS) else 0.0

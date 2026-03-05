import os
from urllib.parse import urlencode

import requests


DEFAULT_QUERIES = [
    "{title} review",
    "{title} criticism",
    "{title} reddit",
]

DOMAIN_ALLOWLIST = {
    "imdb.com": ["imdb", "imdb.com"],
    "rottentomatoes.com": ["rottentomatoes", "rottentomatoes.com"],
    "metacritic.com": ["metacritic", "metacritic.com"],
    "letterboxd.com": ["letterboxd", "letterboxd.com"],
    "reddit.com": ["reddit", "reddit.com"],
}


class SearchError(RuntimeError):
    pass


def search_review_pages(title, sources=None, max_results=20):
    sources = sources or []
    serp_key = os.getenv("SERPAPI_KEY")
    if not serp_key:
        raise SearchError("SERPAPI_KEY is not set")

    allowed_domains = _resolve_domains(sources)
    results = []
    for template in DEFAULT_QUERIES:
        query = template.format(title=title)
        params = {
            "engine": "google",
            "q": query,
            "api_key": serp_key,
            "num": max_results,
        }
        url = f"https://serpapi.com/search?{urlencode(params)}"
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        payload = response.json()
        for item in payload.get("organic_results", []):
            link = item.get("link")
            if not link:
                continue
            if allowed_domains and not _domain_allowed(link, allowed_domains):
                continue
            results.append(
                {
                    "url": link,
                    "title": item.get("title"),
                    "snippet": item.get("snippet"),
                }
            )

    unique = []
    seen = set()
    for r in results:
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        unique.append(r)
    return unique[:max_results]


def _resolve_domains(sources):
    domains = set()
    for source in sources:
        source = source.lower()
        for domain, aliases in DOMAIN_ALLOWLIST.items():
            if source in aliases:
                domains.add(domain)
    return domains


def _domain_allowed(url, allowed_domains):
    return any(domain in url for domain in allowed_domains)

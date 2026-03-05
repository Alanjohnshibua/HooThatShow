import random
import re
import time
from urllib.parse import urlparse
import urllib.robotparser as robotparser

import requests
from bs4 import BeautifulSoup

from scraping.models import ReviewSnippet, SourcePage


USER_AGENT = "HooThatShowBot/0.1 (+https://example.com/bot)"
JS_DOMAINS = {"imdb.com", "rottentomatoes.com"}
RATE_LIMIT_SECONDS = 2
_LAST_FETCH = {}


def fetch_reviews_for_urls(analysis_request, urls):
    snippets = []
    for item in urls:
        url = item["url"] if isinstance(item, dict) else item
        domain = urlparse(url).netloc.replace("www.", "")

        if not _robots_ok(url):
            SourcePage.objects.update_or_create(
                url=url,
                defaults={"domain": domain, "robots_ok": False, "fetch_method": "blocked"},
            )
            continue

        _rate_limit(domain)
        if domain in JS_DOMAINS:
            html = _fetch_with_playwright(url)
            fetch_method = "playwright"
        else:
            html = _fetch_with_requests(url)
            fetch_method = "requests"

        if not html:
            continue

        source_page, _ = SourcePage.objects.update_or_create(
            url=url,
            defaults={"domain": domain, "robots_ok": True, "fetch_method": fetch_method},
        )

        extracted = _extract_review_texts(html)
        for text in extracted:
            if len(text) < 40:
                continue
            snippet = ReviewSnippet.objects.create(
                source_page=source_page,
                analysis_request=analysis_request,
                text=text,
            )
            snippets.append(
                {
                    "text": snippet.text,
                    "domain": source_page.domain,
                    "rating": snippet.rating,
                    "author": snippet.author,
                    "date": snippet.date,
                }
            )
    return snippets


def _rate_limit(domain):
    last_time = _LAST_FETCH.get(domain)
    if last_time:
        elapsed = time.time() - last_time
        if elapsed < RATE_LIMIT_SECONDS:
            time.sleep(RATE_LIMIT_SECONDS - elapsed + random.uniform(0.1, 0.5))
    _LAST_FETCH[domain] = time.time()


def _robots_ok(url):
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return False


def _fetch_with_requests(url):
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return ""


def _fetch_with_playwright(url):
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            html = page.content()
            browser.close()
            return html
    except Exception:
        return ""


def _extract_review_texts(html):
    soup = BeautifulSoup(html, "html.parser")
    texts = []

    for block in soup.find_all(["article", "div"], class_=re.compile(r"(review|critic|comment|content)", re.I)):
        block_text = " ".join(p.get_text(" ", strip=True) for p in block.find_all("p"))
        if block_text:
            texts.append(block_text)

    if not texts:
        for p in soup.find_all("p"):
            text = p.get_text(" ", strip=True)
            if text:
                texts.append(text)

    return list(dict.fromkeys(texts))[:50]

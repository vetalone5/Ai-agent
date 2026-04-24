import logging
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from selectolax.parser import HTMLParser

from src.config.settings import settings

logger = logging.getLogger(__name__)


class Crawler:
    """Lightweight async crawler for on-page SEO analysis."""

    def __init__(self, base_url: str | None = None, max_pages: int = 200) -> None:
        self._base_url = base_url or settings.target_site_url
        self._max_pages = max_pages
        self._http = httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": "SEOAgentBot/1.0 (+https://spioniro.ru)"},
        )

    async def crawl_site(self) -> list[dict[str, Any]]:
        """Crawl the target site and return page data."""
        visited: set[str] = set()
        queue: list[str] = [self._base_url]
        pages: list[dict[str, Any]] = []

        while queue and len(visited) < self._max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            page_data = await self.analyze_page(url)
            if not page_data:
                continue
            pages.append(page_data)

            for link in page_data.get("internal_links", []):
                if link not in visited and self._is_same_domain(link):
                    queue.append(link)

        logger.info("Crawled %d pages from %s", len(pages), self._base_url)
        return pages

    async def analyze_page(self, url: str) -> dict[str, Any] | None:
        """Fetch and analyze a single page."""
        try:
            resp = await self._http.get(url)
            elapsed_ms = int(resp.elapsed.total_seconds() * 1000)

            if "text/html" not in resp.headers.get("content-type", ""):
                return None

            tree = HTMLParser(resp.text)
            return {
                "url": str(resp.url),
                "status_code": resp.status_code,
                "load_time_ms": elapsed_ms,
                "title": self._get_text(tree, "title"),
                "meta_description": self._get_meta(tree, "description"),
                "h1": self._get_text(tree, "h1"),
                "h2_list": [n.text(strip=True) for n in tree.css("h2")],
                "word_count": self._count_words(tree),
                "has_canonical": self._has_canonical(tree),
                "canonical_url": self._get_canonical(tree),
                "has_schema": "application/ld+json" in resp.text,
                "schema_types": self._extract_schema_types(resp.text),
                "images_without_alt": self._count_images_no_alt(tree),
                "internal_links": self._extract_internal_links(tree, url),
                "internal_links_count": len(self._extract_internal_links(tree, url)),
                "external_links_count": len(self._extract_external_links(tree, url)),
                "has_og_tags": self._has_og(tree),
                "issues": self._detect_issues(resp, tree, url),
            }
        except Exception as e:
            logger.warning("Failed to crawl %s: %s", url, e)
            return {"url": url, "status_code": 0, "error": str(e), "issues": [{"type": "crawl_error", "severity": "critical", "detail": str(e)}]}

    def _detect_issues(self, resp: httpx.Response, tree: HTMLParser, url: str) -> list[dict[str, Any]]:
        issues = []
        title = self._get_text(tree, "title")
        desc = self._get_meta(tree, "description")
        h1 = self._get_text(tree, "h1")
        word_count = self._count_words(tree)

        if resp.status_code >= 400:
            issues.append({"type": "http_error", "severity": "critical", "detail": f"HTTP {resp.status_code}"})
        if not title:
            issues.append({"type": "missing_title", "severity": "high", "detail": "No <title> tag"})
        elif len(title) > 70:
            issues.append({"type": "title_too_long", "severity": "medium", "detail": f"Title {len(title)} chars (max 60)"})
        if not desc:
            issues.append({"type": "missing_description", "severity": "high", "detail": "No meta description"})
        elif len(desc) > 170:
            issues.append({"type": "description_too_long", "severity": "low", "detail": f"Description {len(desc)} chars (max 160)"})
        if not h1:
            issues.append({"type": "missing_h1", "severity": "high", "detail": "No H1 tag"})
        if len(tree.css("h1")) > 1:
            issues.append({"type": "multiple_h1", "severity": "medium", "detail": f"{len(tree.css('h1'))} H1 tags"})
        if h1 and title and h1 == title:
            issues.append({"type": "h1_equals_title", "severity": "low", "detail": "H1 is identical to Title"})
        if word_count < 300 and "/blog" in url:
            issues.append({"type": "thin_content", "severity": "high", "detail": f"Only {word_count} words"})
        if self._count_images_no_alt(tree) > 0:
            issues.append({"type": "images_no_alt", "severity": "medium", "detail": f"{self._count_images_no_alt(tree)} images without alt"})
        if not self._has_canonical(tree):
            issues.append({"type": "missing_canonical", "severity": "medium", "detail": "No canonical tag"})

        return issues

    def _is_same_domain(self, url: str) -> bool:
        base_domain = urlparse(self._base_url).netloc
        return urlparse(url).netloc == base_domain

    def _extract_internal_links(self, tree: HTMLParser, current_url: str) -> list[str]:
        links = set()
        for a in tree.css("a[href]"):
            href = a.attributes.get("href", "")
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            full_url = urljoin(current_url, href)
            if self._is_same_domain(full_url):
                links.add(full_url.split("#")[0].split("?")[0])
        return list(links)

    def _extract_external_links(self, tree: HTMLParser, current_url: str) -> list[str]:
        links = set()
        for a in tree.css("a[href]"):
            href = a.attributes.get("href", "")
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            full_url = urljoin(current_url, href)
            if not self._is_same_domain(full_url) and full_url.startswith("http"):
                links.add(full_url)
        return list(links)

    @staticmethod
    def _get_text(tree: HTMLParser, tag: str) -> str:
        node = tree.css_first(tag)
        return node.text(strip=True) if node else ""

    @staticmethod
    def _get_meta(tree: HTMLParser, name: str) -> str:
        node = tree.css_first(f'meta[name="{name}"]')
        return node.attributes.get("content", "") if node else ""

    @staticmethod
    def _get_canonical(tree: HTMLParser) -> str:
        node = tree.css_first('link[rel="canonical"]')
        return node.attributes.get("href", "") if node else ""

    @staticmethod
    def _has_canonical(tree: HTMLParser) -> bool:
        return tree.css_first('link[rel="canonical"]') is not None

    @staticmethod
    def _has_og(tree: HTMLParser) -> bool:
        return tree.css_first('meta[property="og:title"]') is not None

    @staticmethod
    def _count_words(tree: HTMLParser) -> int:
        body = tree.css_first("article") or tree.css_first("main") or tree.css_first("body")
        if not body:
            return 0
        text = body.text(separator=" ", strip=True)
        return len(text.split())

    @staticmethod
    def _count_images_no_alt(tree: HTMLParser) -> int:
        return sum(1 for img in tree.css("img") if not img.attributes.get("alt"))

    @staticmethod
    def _extract_schema_types(html: str) -> list[str]:
        import json
        types = []
        start = 0
        while True:
            idx = html.find('"@type"', start)
            if idx == -1:
                break
            colon = html.find(":", idx)
            quote1 = html.find('"', colon + 1)
            quote2 = html.find('"', quote1 + 1)
            if quote1 != -1 and quote2 != -1:
                types.append(html[quote1 + 1 : quote2])
            start = idx + 1
        return types

from __future__ import annotations

import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


USER_AGENT = "TKKGTrackerCatalogueBot/1.0 (+https://github.com/OliverZsuffa/TKKGtracker)"


class SourceAccessError(RuntimeError):
    """Raised when a source cannot be fetched safely."""


class SourceClient:
    def __init__(self, delay_seconds: float = 0.35) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.delay_seconds = delay_seconds
        self._robots: dict[str, RobotFileParser | None] = {}
        self._robots_errors: dict[str, str] = {}
        self._cache: dict[str, bytes] = {}
        self._last_request = 0.0

    def _robots_for(self, url: str) -> RobotFileParser | None:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin in self._robots_errors:
            raise SourceAccessError(self._robots_errors[origin])
        if origin in self._robots:
            return self._robots[origin]
        robots_url = f"{origin}/robots.txt"
        try:
            response = self.session.get(robots_url, timeout=20)
        except requests.RequestException as exc:
            message = f"Could not check robots.txt for {origin}: {exc}"
            self._robots_errors[origin] = message
            raise SourceAccessError(message) from exc
        if response.status_code == 404:
            self._robots[origin] = None
            return None
        if response.status_code != 200:
            message = f"Could not verify robots.txt for {origin}: HTTP {response.status_code}"
            self._robots_errors[origin] = message
            raise SourceAccessError(message)
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        self._robots[origin] = parser
        return parser

    def get_html(self, url: str) -> BeautifulSoup:
        if url in self._cache:
            return BeautifulSoup(self._cache[url], "html.parser")
        parser = self._robots_for(url)
        if parser is not None and not parser.can_fetch(USER_AGENT, url):
            raise SourceAccessError(f"robots.txt disallows fetching {url}")
        wait = self.delay_seconds - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        try:
            response = self.session.get(url, timeout=30)
            self._last_request = time.monotonic()
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SourceAccessError(f"Could not fetch {url}: {exc}") from exc
        if "text/html" not in response.headers.get("Content-Type", "").lower():
            raise SourceAccessError(f"Expected HTML at {url}, got {response.headers.get('Content-Type', 'unknown')}")
        self._cache[url] = response.content
        return BeautifulSoup(response.content, "html.parser")

"""Financial news RSS crawler.

Fetches market news from Economic Times and LiveMint RSS feeds.
These are plain XML feeds — no JS execution or auth required.

Sources:
  - ET Markets:  https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms
  - LiveMint:    https://www.livemint.com/rss/markets

RSS item structure (standard):
  <item>
    <title>...</title>
    <link>...</link>
    <description>...</description>
    <pubDate>Sun, 03 May 2026 18:30:00 +0530</pubDate>
    <guid>...</guid>
  </item>
"""

import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

RSS_FEEDS: Dict[str, str] = {
    "economic_times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "livemint":       "https://www.livemint.com/rss/markets",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml,application/xml,text/xml,*/*;q=0.8",
}


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


class NewsRSSCrawler:
    """Crawler for financial news from ET Markets and LiveMint RSS feeds.

    Usage:
        crawler = NewsRSSCrawler()

        # Fetch from all feeds
        articles = crawler.crawl()

        # Fetch from a specific feed
        articles = crawler.crawl(feeds=["economic_times"])
    """

    def __init__(self):
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = _build_session()
        return self._session

    def crawl(
        self,
        feeds: Optional[List[str]] = None,
        max_items_per_feed: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch news articles from RSS feeds.

        Args:
            feeds:              List of feed names from RSS_FEEDS.
                                None = fetch all feeds.
            max_items_per_feed: Max articles per feed.

        Returns:
            List of article dicts with keys:
                title, link, description, pub_date, guid, feed_name, source
        """
        feed_list = feeds or list(RSS_FEEDS.keys())
        all_articles: List[Dict[str, Any]] = []

        for feed_name in feed_list:
            url = RSS_FEEDS.get(feed_name)
            if not url:
                logger.warning("Unknown feed: %s", feed_name)
                continue

            articles = self._fetch_feed(feed_name, url, max_items_per_feed)
            all_articles.extend(articles)
            time.sleep(0.5)  # Brief pause between feeds

        logger.info("News RSS: fetched %d articles from %d feeds", len(all_articles), len(feed_list))
        return all_articles

    def _fetch_feed(
        self,
        feed_name: str,
        url: str,
        max_items: int,
    ) -> List[Dict[str, Any]]:
        """Fetch and parse a single RSS feed."""
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("RSS fetch failed for %s: %s", feed_name, exc)
            return []

        return self._parse_rss(resp.text, feed_name, max_items)

    def _parse_rss(
        self,
        xml_text: str,
        feed_name: str,
        max_items: int,
    ) -> List[Dict[str, Any]]:
        """Parse RSS XML into article dicts."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.error("XML parse error for %s: %s", feed_name, exc)
            return []

        articles: List[Dict[str, Any]] = []
        channel = root.find("channel")
        if channel is None:
            logger.warning("No <channel> in RSS for %s", feed_name)
            return []

        items = channel.findall("item")

        for item in items[:max_items]:
            title = self._get_text(item, "title")
            link = self._get_text(item, "link")
            description = self._get_text(item, "description")
            pub_date_str = self._get_text(item, "pubDate")
            guid = self._get_text(item, "guid")

            # Parse pub_date
            pub_date = self._parse_date(pub_date_str)

            # Clean description (strip HTML)
            if description:
                import re
                description = re.sub(r"<[^>]+>", "", description).strip()
                # Truncate very long descriptions
                if len(description) > 500:
                    description = description[:497] + "..."

            articles.append({
                "title":       title,
                "link":        link,
                "description": description,
                "pub_date":    pub_date,
                "pub_date_raw": pub_date_str,
                "guid":        guid,
                "feed_name":   feed_name,
                "source":      f"RSS_{feed_name}",
            })

        logger.info("RSS %s: parsed %d articles", feed_name, len(articles))
        return articles

    @staticmethod
    def _get_text(element: ET.Element, tag: str) -> str:
        """Safely get text from an XML element."""
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return ""

    @staticmethod
    def _parse_date(date_str: str) -> Optional[str]:
        """Parse RSS date format to ISO format."""
        if not date_str:
            return None
        # Common RSS date formats
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",      # "Sun, 03 May 2026 18:30:00 +0530"
            "%a, %d %b %Y %H:%M:%S GMT",      # "Sun, 03 May 2026 18:30:00 GMT"
            "%Y-%m-%dT%H:%M:%S%z",            # ISO 8601
            "%d %b %Y %H:%M:%S %z",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.isoformat()
            except ValueError:
                continue
        return date_str  # Return as-is if unparseable

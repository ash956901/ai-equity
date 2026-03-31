"""News aggregation service with sentiment and category enrichment."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import threading
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

from src.config import get_settings

logger = logging.getLogger(__name__)


class NewsService:
    """Fetches and enriches market news from public RSS feeds."""

    _model_lock = threading.Lock()
    _log_lock = threading.Lock()
    _sentiment_pipeline = None
    _zero_shot_pipeline = None
    _loaded_sentiment_model: Optional[str] = None
    _loaded_zero_shot_model: Optional[str] = None

    MAX_NEWS_PER_REQUEST = 50
    MAX_FEED_RETRIES = 3
    MAX_FEED_CONCURRENCY = 3
    NEWS_REQUEST_LOG_FILE = Path(__file__).resolve().parents[3] / "logs" / "news_request.log"

    GOOGLE_FINANCE_QUERIES = [
        "stock market",
        "company earnings",
        "finance india",
        "global economy",
    ]
    REUTERS_RSS_FEEDS = [
        "https://news.google.com/rss/search?q=site:reuters.com+business+markets&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=site:reuters.com+economy+finance&hl=en-US&gl=US&ceid=US:en",
    ]
    YAHOO_FINANCE_RSS_FEEDS = [
        "https://finance.yahoo.com/news/rssindex",
    ]

    # Broad market taxonomy for multi-label categorization.
    ZERO_SHOT_CANDIDATE_LABELS = [
        "equities",
        "bonds",
        "commodities",
        "foreign exchange",
        "cryptocurrency",
        "banking",
        "earnings",
        "mergers and acquisitions",
        "regulation",
        "macroeconomy",
        "inflation",
        "interest rates",
        "monetary policy",
        "geopolitics",
        "technology",
        "energy",
        "healthcare",
        "consumer goods",
        "industrials",
        "real estate",
        "automotive",
        "telecommunications",
        "supply chain",
        "environmental social governance",
        "litigation",
        "analyst ratings",
        "initial public offering",
        "dividends and buybacks",
        "corporate guidance",
    ]
    GENERIC_QUERY_TOKENS = {
        "LIMITED",
        "LTD",
        "INC",
        "INCORPORATED",
        "CORP",
        "CORPORATION",
        "COMPANY",
        "HOLDINGS",
        "GROUP",
        "PRIVATE",
        "PUBLIC",
    }

    async def get_news(self, limit: int = MAX_NEWS_PER_REQUEST, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return deduplicated market news with sentiment and categories."""
        safe_limit = min(max(limit, 1), self.MAX_NEWS_PER_REQUEST)
        cleaned_query = self._clean_query(query)
        raw_articles, source_logs = await self._fetch_all_sources(query=cleaned_query)
        deduplicated = self._deduplicate_and_clean(raw_articles)
        deduplicated.sort(
            key=lambda article: article.get("published_at") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        if cleaned_query:
            deduplicated = self._prioritize_query_matches(deduplicated, cleaned_query)

        selected = deduplicated[:safe_limit]
        await self._enrich_articles(selected)

        self._write_request_log(
            requested_limit=safe_limit,
            query=cleaned_query,
            source_logs=source_logs,
            raw_count=len(raw_articles),
            deduplicated_count=len(deduplicated),
            selected_articles=selected,
        )
        return selected

    async def _fetch_all_sources(self, query: Optional[str] = None) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Fetch all RSS feeds concurrently."""
        dynamic_queries = self._build_query_queries(query)
        google_queries = dynamic_queries + self.GOOGLE_FINANCE_QUERIES
        deduped_google_queries = list(dict.fromkeys(google_queries))
        google_feeds = [
            f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"
            for query in deduped_google_queries
        ]
        all_feeds = (
            [("Google News", url) for url in google_feeds]
            + [("Reuters", url) for url in self.REUTERS_RSS_FEEDS]
            + [("Yahoo Finance", url) for url in self.YAHOO_FINANCE_RSS_FEEDS]
        )

        timeout = httpx.Timeout(15.0)
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers=self._default_request_headers(),
        ) as client:
            semaphore = asyncio.Semaphore(self.MAX_FEED_CONCURRENCY)
            tasks = [
                self._fetch_single_feed_with_semaphore(semaphore, client, source_name, feed_url)
                for source_name, feed_url in all_feeds
            ]
            results = await asyncio.gather(*tasks)

        articles: List[Dict[str, Any]] = []
        source_logs: List[Dict[str, Any]] = []
        for result in results:
            source_logs.append(result)
            if result.get("error"):
                logger.warning(
                    "Failed to fetch feed %s (%s): %s",
                    result.get("source"),
                    result.get("feed_url"),
                    result.get("error"),
                )
                continue
            articles.extend(result.get("articles") or [])
        return articles, source_logs

    async def _fetch_single_feed_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        client: httpx.AsyncClient,
        source_name: str,
        feed_url: str,
    ) -> Dict[str, Any]:
        """Bound feed fetch concurrency to reduce rate-limit bursts."""
        async with semaphore:
            return await self._fetch_single_feed(client, source_name, feed_url)

    async def _fetch_single_feed(
        self,
        client: httpx.AsyncClient,
        source_name: str,
        feed_url: str,
    ) -> Dict[str, Any]:
        """Fetch and parse a single RSS/Atom feed."""
        last_error: Optional[str] = None
        last_status_code: Optional[int] = None

        for attempt in range(1, self.MAX_FEED_RETRIES + 1):
            try:
                # Add slight per-attempt jitter to avoid synchronized provider bursts.
                await asyncio.sleep(0.2 * attempt)
                response = await client.get(feed_url)
                last_status_code = response.status_code
                response.raise_for_status()

                articles = self._parse_feed(source_name=source_name, feed_url=feed_url, xml_text=response.text)
                return {
                    "source": source_name,
                    "feed_url": feed_url,
                    "status_code": last_status_code,
                    "error": None,
                    "articles": articles,
                }
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                last_status_code = status_code
                last_error = str(exc)

                # Retry transient/rate-limit classes only.
                if status_code in {429, 500, 502, 503, 504} and attempt < self.MAX_FEED_RETRIES:
                    await asyncio.sleep(1.2 * attempt)
                    continue
                break
            except Exception as exc:
                last_error = str(exc)
                if attempt < self.MAX_FEED_RETRIES:
                    await asyncio.sleep(1.0 * attempt)
                    continue
                break

        return {
            "source": source_name,
            "feed_url": feed_url,
            "status_code": last_status_code,
            "error": last_error,
            "articles": [],
        }

    @staticmethod
    def _default_request_headers() -> Dict[str, str]:
        """Headers tuned to reduce RSS provider bot/rate-limit blocks."""
        return {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }

    def _write_request_log(
        self,
        requested_limit: int,
        query: Optional[str],
        source_logs: List[Dict[str, Any]],
        raw_count: int,
        deduplicated_count: int,
        selected_articles: List[Dict[str, Any]],
    ) -> None:
        """Rewrite request log with full details for current request only."""
        try:
            self.NEWS_REQUEST_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

            with self._log_lock:
                with self.NEWS_REQUEST_LOG_FILE.open("w", encoding="utf-8") as log_file:
                    now = datetime.now(tz=timezone.utc).isoformat()
                    log_file.write(f"news request timestamp (utc): {now}\n")
                    log_file.write(f"requested limit: {requested_limit}\n")
                    log_file.write(f"query: {query or 'none'}\n")
                    log_file.write(f"raw fetched articles: {raw_count}\n")
                    log_file.write(f"after deduplication: {deduplicated_count}\n")
                    log_file.write(f"returned articles: {len(selected_articles)}\n\n")

                    log_file.write("=== per feed results ===\n")
                    for feed_log in source_logs:
                        log_file.write(
                            "source={source} status={status} feed={feed} error={error} count={count}\n".format(
                                source=feed_log.get("source"),
                                status=feed_log.get("status_code"),
                                feed=feed_log.get("feed_url"),
                                error=feed_log.get("error") or "none",
                                count=len(feed_log.get("articles") or []),
                            )
                        )
                        for article in feed_log.get("articles") or []:
                            published_at = article.get("published_at")
                            published_text = (
                                published_at.isoformat()
                                if isinstance(published_at, datetime)
                                else str(published_at)
                            )
                            log_file.write(
                                "  - title={title} | url={url} | published_at={published}\n".format(
                                    title=article.get("title") or "",
                                    url=article.get("url") or "",
                                    published=published_text,
                                )
                            )
                        log_file.write("\n")

                    log_file.write("=== returned payload (post-dedup + enriched) ===\n")
                    for article in selected_articles:
                        published_at = article.get("published_at")
                        published_text = (
                            published_at.isoformat()
                            if isinstance(published_at, datetime)
                            else str(published_at)
                        )
                        categories = ", ".join(article.get("categories") or [])
                        log_file.write(
                            "source={source} | title={title} | sentiment={sentiment}({score}) | categories=[{categories}] | url={url} | published_at={published}\n".format(
                                source=article.get("source") or "",
                                title=article.get("title") or "",
                                sentiment=article.get("sentiment") or "",
                                score=article.get("sentiment_confidence") or 0.0,
                                categories=categories,
                                url=article.get("url") or "",
                                published=published_text,
                            )
                        )
        except Exception as exc:
            logger.error("Failed to write news request log: %s", exc)

    @staticmethod
    def _clean_query(value: Optional[str]) -> Optional[str]:
        """Normalize query by collapsing whitespace."""
        if not value:
            return None
        cleaned = " ".join(value.split()).strip()
        return cleaned or None

    @classmethod
    def _build_query_queries(cls, query: Optional[str]) -> List[str]:
        """Expand user query into market-friendly Google News searches."""
        if not query:
            return []

        return [
            f'"{query}" stock',
            f'"{query}" shares',
            f'"{query}" earnings',
            query,
        ]

    @classmethod
    def _prioritize_query_matches(cls, articles: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Rank query-relevant stories ahead of generic market news."""
        normalized_query = cls._normalize_match_text(query)
        if not normalized_query:
            return articles

        query_tokens = [
            token
            for token in normalized_query.split()
            if len(token) >= 3 and token not in cls.GENERIC_QUERY_TOKENS
        ]
        normalized_core_query = " ".join(query_tokens) if query_tokens else normalized_query
        compact_terms = {
            normalized_query.replace(" ", ""),
            normalized_core_query.replace(" ", ""),
        }
        compact_terms = {term for term in compact_terms if term}
        feed_markers = [quote_plus(item).lower() for item in cls._build_query_queries(query)]

        scored_rows: List[tuple[int, datetime, Dict[str, Any]]] = []
        for article in articles:
            score = cls._query_match_score(
                article=article,
                normalized_query=normalized_query,
                normalized_core_query=normalized_core_query,
                query_tokens=query_tokens,
                compact_terms=compact_terms,
                feed_markers=feed_markers,
            )
            published_at = article.get("published_at")
            if not isinstance(published_at, datetime):
                published_at = datetime.min.replace(tzinfo=timezone.utc)
            scored_rows.append((score, published_at, article))

        if not any(score > 0 for score, _, _ in scored_rows):
            return articles

        scored_rows.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return [article for _, _, article in scored_rows]

    @classmethod
    def _query_match_score(
        cls,
        article: Dict[str, Any],
        normalized_query: str,
        normalized_core_query: str,
        query_tokens: List[str],
        compact_terms: set[str],
        feed_markers: List[str],
    ) -> int:
        """Compute lightweight relevance score for a query/article pair."""
        text = f"{article.get('title') or ''} {article.get('summary') or ''}"
        normalized_text = cls._normalize_match_text(text)
        if not normalized_text:
            return 0

        padded_text = f" {normalized_text} "
        compact_text = normalized_text.replace(" ", "")
        score = 0

        if normalized_query and normalized_query in normalized_text:
            score += 6
        if normalized_core_query and normalized_core_query != normalized_query and normalized_core_query in normalized_text:
            score += 5

        for term in compact_terms:
            if len(term) >= 4 and term in compact_text:
                score += 7
                break

        matched_tokens = 0
        for token in query_tokens:
            if f" {token} " in padded_text:
                matched_tokens += 1

        if matched_tokens:
            score += matched_tokens * 2
            if matched_tokens == len(query_tokens):
                score += 2

        source_feed = str(article.get("source_feed") or "").lower()
        if source_feed and any(marker in source_feed for marker in feed_markers):
            score += 1

        return score

    @staticmethod
    def _normalize_match_text(value: str) -> str:
        """Normalize text for stable ticker/company matching."""
        return " ".join(re.sub(r"[^A-Z0-9 ]+", " ", value.upper()).split())

    def _parse_feed(self, source_name: str, feed_url: str, xml_text: str) -> List[Dict[str, Any]]:
        """Parse RSS/Atom XML into normalized article records."""
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as exc:
            logger.warning("Unable to parse feed XML for %s (%s): %s", source_name, feed_url, exc)
            return []

        entries = root.findall(".//item")
        if not entries:
            entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")

        articles: List[Dict[str, Any]] = []
        for entry in entries:
            title = self._first_text(entry, ["title", "{http://www.w3.org/2005/Atom}title"])
            link = self._first_link(entry)
            summary = self._first_text(
                entry,
                [
                    "description",
                    "summary",
                    "content",
                    "{http://www.w3.org/2005/Atom}summary",
                ],
            )
            published_raw = self._first_text(
                entry,
                [
                    "pubDate",
                    "published",
                    "updated",
                    "{http://www.w3.org/2005/Atom}published",
                    "{http://www.w3.org/2005/Atom}updated",
                ],
            )
            published_at = self._parse_datetime(published_raw)

            if not title and not summary:
                continue

            articles.append(
                {
                    "source": source_name,
                    "source_feed": feed_url,
                    "title": self._clean_text(title),
                    "summary": self._clean_text(summary),
                    "url": link,
                    "published_at": published_at,
                }
            )

        return articles

    def _deduplicate_and_clean(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate by URL and normalized headline fingerprint."""
        seen_keys = set()
        deduplicated: List[Dict[str, Any]] = []

        for article in articles:
            title = (article.get("title") or "").strip().lower()
            url = (article.get("url") or "").strip().lower()
            fingerprint_source = f"{title}|{url}" if url else title

            if not fingerprint_source:
                continue

            key = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
            if key in seen_keys:
                continue

            seen_keys.add(key)
            deduplicated.append(article)

        return deduplicated

    async def _enrich_articles(self, articles: List[Dict[str, Any]]) -> None:
        """Add FinBERT sentiment and multi-label zero-shot categories."""
        if not articles:
            return

        sentiment_pipeline, zero_shot_pipeline = self._get_or_create_pipelines()
        if sentiment_pipeline is None or zero_shot_pipeline is None:
            logger.warning("AI pipelines unavailable; returning uncategorized neutral metadata")
            for article in articles:
                article["sentiment"] = "neutral"
                article["sentiment_confidence"] = 0.0
                article["categories"] = []
            return

        texts = [self._build_model_text(article) for article in articles]

        try:
            sentiment_results = sentiment_pipeline(texts, truncation=True)
        except Exception as exc:
            logger.error("FinBERT inference failed: %s", exc)
            sentiment_results = [{"label": "neutral", "score": 0.0} for _ in texts]

        for article, sentiment in zip(articles, sentiment_results):
            article["sentiment"] = str(sentiment.get("label", "neutral")).lower()
            article["sentiment_confidence"] = float(sentiment.get("score", 0.0))

        for article, text in zip(articles, texts):
            try:
                zero_shot_result = zero_shot_pipeline(
                    sequences=text,
                    candidate_labels=self.ZERO_SHOT_CANDIDATE_LABELS,
                    multi_label=True,
                )
                article["categories"] = self._extract_categories(zero_shot_result)
            except Exception as exc:
                logger.error("Zero-shot inference failed for article '%s': %s", article.get("title"), exc)
                article["categories"] = []

    @classmethod
    def _get_or_create_pipelines(cls):
        """Lazily initialize Hugging Face pipelines once per process."""
        settings = get_settings()
        sentiment_model = settings.news_sentiment_model
        zero_shot_model = settings.news_zero_shot_model

        if (
            cls._sentiment_pipeline is not None
            and cls._zero_shot_pipeline is not None
            and cls._loaded_sentiment_model == sentiment_model
            and cls._loaded_zero_shot_model == zero_shot_model
        ):
            return cls._sentiment_pipeline, cls._zero_shot_pipeline

        with cls._model_lock:
            settings = get_settings()
            sentiment_model = settings.news_sentiment_model
            zero_shot_model = settings.news_zero_shot_model

            if (
                cls._sentiment_pipeline is not None
                and cls._zero_shot_pipeline is not None
                and cls._loaded_sentiment_model == sentiment_model
                and cls._loaded_zero_shot_model == zero_shot_model
            ):
                return cls._sentiment_pipeline, cls._zero_shot_pipeline

            try:
                from transformers import pipeline

                cls._sentiment_pipeline = pipeline(
                    task="text-classification",
                    model=sentiment_model,
                )
                cls._zero_shot_pipeline = pipeline(
                    task="zero-shot-classification",
                    model=zero_shot_model,
                )
                cls._loaded_sentiment_model = sentiment_model
                cls._loaded_zero_shot_model = zero_shot_model
                logger.info(
                    "Initialized news NLP pipelines: sentiment='%s', zero_shot='%s'",
                    sentiment_model,
                    zero_shot_model,
                )
            except Exception as exc:
                logger.error("Failed to initialize NLP pipelines: %s", exc)
                cls._sentiment_pipeline = None
                cls._zero_shot_pipeline = None
                cls._loaded_sentiment_model = None
                cls._loaded_zero_shot_model = None

        return cls._sentiment_pipeline, cls._zero_shot_pipeline

    @staticmethod
    def _build_model_text(article: Dict[str, Any]) -> str:
        """Compose bounded text input for classifiers."""
        title = article.get("title") or ""
        summary = article.get("summary") or ""
        merged = f"{title}. {summary}".strip()
        return merged[:1200]

    @staticmethod
    def _extract_categories(zero_shot_result: Dict[str, Any]) -> List[str]:
        """Pick categories whose zero-shot confidence is above 60%."""
        labels = zero_shot_result.get("labels") or []
        scores = zero_shot_result.get("scores") or []
        selected: List[str] = []

        for label, score in zip(labels, scores):
            if float(score) >= 0.60:
                selected.append(str(label))
            if len(selected) >= 5:
                break

        return selected

    @staticmethod
    def _first_text(entry: ElementTree.Element, tags: List[str]) -> Optional[str]:
        """Return first non-empty text content for a set of XML tags."""
        for tag in tags:
            element = entry.find(tag)
            if element is not None and element.text:
                text = element.text.strip()
                if text:
                    return text
        return None

    @staticmethod
    def _first_link(entry: ElementTree.Element) -> Optional[str]:
        """Extract URL from RSS or Atom link nodes."""
        link_element = entry.find("link")
        if link_element is not None:
            if link_element.text and link_element.text.strip():
                return link_element.text.strip()
            href = link_element.attrib.get("href")
            if href:
                return href.strip()

        atom_link = entry.find("{http://www.w3.org/2005/Atom}link")
        if atom_link is not None:
            href = atom_link.attrib.get("href")
            if href:
                return href.strip()

        return None

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> datetime:
        """Parse publication date and normalize timezone."""
        if not value:
            return datetime.now(tz=timezone.utc)

        parsed: Optional[datetime] = None
        try:
            parsed = parsedate_to_datetime(value)
        except Exception:
            parsed = None

        if parsed is None:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                return datetime.now(tz=timezone.utc)

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _clean_text(value: Optional[str]) -> str:
        """Decode entities, strip HTML, and normalize whitespace."""
        if not value:
            return ""

        text = unescape(value)
        text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
        return " ".join(text.split())

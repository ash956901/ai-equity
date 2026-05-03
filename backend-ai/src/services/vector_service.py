"""Vector search and indexing service (Qdrant).

Centralizes all collection definitions, ensures collections exist with the
correct dimension, and exposes both ``search_*`` and ``index_*`` helpers
used by ETL pipelines and agent tools.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from src.config import get_settings
from src.llm import get_embedding_dim, get_embeddings

logger = logging.getLogger(__name__)


COLLECTION_FILINGS = "company_filings"
COLLECTION_NEWS = "news_articles"
COLLECTION_TRANSCRIPTS = "transcripts"
COLLECTION_SOCIAL = "social_posts"
COLLECTION_USER_UPLOADS = "user_uploads"

ALL_COLLECTIONS = [
    COLLECTION_FILINGS,
    COLLECTION_NEWS,
    COLLECTION_TRANSCRIPTS,
    COLLECTION_SOCIAL,
    COLLECTION_USER_UPLOADS,
]


class VectorService:
    """Service for semantic search and indexing across Qdrant collections."""

    def __init__(self):
        self.settings = get_settings()
        self._client = None

    # --------------------------------------------------------------------- #
    #  Client + collection management                                       #
    # --------------------------------------------------------------------- #

    def _get_client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient

                self._client = QdrantClient(
                    url=self.settings.qdrant_url,
                    api_key=self.settings.qdrant_api_key,
                )
            except Exception as exc:
                logger.warning("Qdrant client init failed: %s", exc)
                return None
        return self._client

    def ensure_collection(self, name: str) -> bool:
        """Create the named collection if it does not exist."""
        client = self._get_client()
        if not client:
            return False
        try:
            from qdrant_client.models import Distance, VectorParams

            existing = {c.name for c in client.get_collections().collections}
            if name not in existing:
                client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=get_embedding_dim(),
                        distance=Distance.COSINE,
                    ),
                )
            return True
        except Exception as exc:
            logger.error("ensure_collection(%s) failed: %s", name, exc)
            return False

    # --------------------------------------------------------------------- #
    #  Embedding helper                                                     #
    # --------------------------------------------------------------------- #

    def _embed_text(self, text: str) -> List[float]:
        try:
            return get_embeddings().embed_query(text)
        except Exception:
            return [0.0] * get_embedding_dim()

    def _embed_documents(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            return get_embeddings().embed_documents(list(texts))
        except Exception:
            dim = get_embedding_dim()
            return [[0.0] * dim for _ in texts]

    # --------------------------------------------------------------------- #
    #  Indexing helpers                                                     #
    # --------------------------------------------------------------------- #

    def index_chunks(
        self,
        collection: str,
        items: List[Dict[str, Any]],
        text_field: str = "text",
    ) -> int:
        """Upsert chunks into a collection.

        Each item must contain ``text`` and a ``payload`` dict; an optional
        ``id`` (string UUID) overrides the auto-generated one.
        """
        client = self._get_client()
        if not client or not items:
            return 0
        if not self.ensure_collection(collection):
            return 0

        from qdrant_client.models import PointStruct

        texts = [item.get(text_field, "") for item in items]
        vectors = self._embed_documents(texts)
        points = []
        for item, vector in zip(items, vectors):
            payload = dict(item.get("payload", {}))
            payload[text_field] = item.get(text_field, "")
            points.append(
                PointStruct(
                    id=item.get("id") or str(uuid.uuid4()),
                    vector=vector,
                    payload=payload,
                )
            )
        batch = 64
        for i in range(0, len(points), batch):
            try:
                client.upsert(collection_name=collection, points=points[i : i + batch])
            except Exception as exc:
                logger.error("Qdrant upsert into %s failed: %s", collection, exc)
                return i
        return len(points)

    def index_filing_pages(
        self, *, company_id: str, filing_id: str, filing_type: str,
        filing_date: Optional[str], pages: List[Dict[str, Any]],
    ) -> int:
        """Convenience wrapper for the document parser ETL task."""
        items: List[Dict[str, Any]] = []
        for page in pages:
            text = page.get("text") or ""
            if not text.strip():
                continue
            for chunk_idx, chunk_text in enumerate(_chunk_text(text)):
                items.append(
                    {
                        "text": chunk_text,
                        "payload": {
                            "company_id": company_id,
                            "filing_id": filing_id,
                            "filing_type": filing_type,
                            "filing_date": filing_date,
                            "page_number": page.get("page_number"),
                            "chunk_index": chunk_idx,
                        },
                    }
                )
        return self.index_chunks(COLLECTION_FILINGS, items)

    def index_news(
        self, articles: List[Dict[str, Any]]
    ) -> int:
        """Index news articles. Each article needs id, headline, body,
        company_id (optional), published_at (iso), source, themes (list)."""
        items: List[Dict[str, Any]] = []
        for art in articles:
            text = (art.get("headline") or "") + "\n" + (art.get("body") or "")
            if not text.strip():
                continue
            items.append(
                {
                    "id": art.get("id"),
                    "text": text,
                    "payload": {
                        "news_id": art.get("id"),
                        "company_id": art.get("company_id"),
                        "headline": art.get("headline"),
                        "source": art.get("source"),
                        "source_url": art.get("source_url"),
                        "published_at": art.get("published_at"),
                        "tickers": art.get("tickers") or [],
                        "themes": art.get("themes") or [],
                    },
                }
            )
        return self.index_chunks(COLLECTION_NEWS, items)

    def index_transcript_segments(
        self,
        *,
        transcript_id: str,
        company_id: str,
        period_label: Optional[str],
        segments: List[Dict[str, Any]],
    ) -> int:
        items: List[Dict[str, Any]] = []
        for seg in segments:
            text = seg.get("text") or ""
            if not text.strip():
                continue
            items.append(
                {
                    "id": seg.get("vector_id"),
                    "text": text,
                    "payload": {
                        "transcript_id": transcript_id,
                        "segment_id": seg.get("segment_id"),
                        "company_id": company_id,
                        "ordinal": seg.get("ordinal"),
                        "speaker_role": seg.get("speaker_role"),
                        "speaker_name": seg.get("speaker_name"),
                        "turn_type": seg.get("turn_type"),
                        "period": period_label,
                    },
                }
            )
        return self.index_chunks(COLLECTION_TRANSCRIPTS, items)

    def index_social_posts(self, posts: List[Dict[str, Any]]) -> int:
        items: List[Dict[str, Any]] = []
        for post in posts:
            text = post.get("body") or ""
            if not text.strip():
                continue
            items.append(
                {
                    "id": post.get("id"),
                    "text": text,
                    "payload": {
                        "post_id": post.get("id"),
                        "source": post.get("source"),
                        "tickers": post.get("tickers") or [],
                        "company_ids": post.get("company_ids") or [],
                        "sentiment_label": post.get("sentiment_label"),
                        "stance_label": post.get("stance_label"),
                        "topic_id": post.get("topic_id"),
                        "posted_at": post.get("posted_at"),
                        "author_handle": post.get("author_handle"),
                        "author_followers": post.get("author_followers"),
                    },
                }
            )
        return self.index_chunks(COLLECTION_SOCIAL, items)

    # --------------------------------------------------------------------- #
    #  Search helpers                                                       #
    # --------------------------------------------------------------------- #

    def search_company_filings(
        self,
        company_id,
        query: str,
        filing_types: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        client = self._get_client()
        if not client:
            return []
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            conditions = [
                FieldCondition(
                    key="company_id",
                    match=MatchValue(value=str(company_id)),
                )
            ]
            if filing_types:
                conditions.append(
                    FieldCondition(
                        key="filing_type",
                        match=MatchValue(any=filing_types),
                    )
                )
            results = client.search(
                collection_name=COLLECTION_FILINGS,
                query_vector=self._embed_text(query),
                query_filter=Filter(must=conditions) if conditions else None,
                limit=limit,
                with_payload=True,
            )
            return [
                {
                    "text": hit.payload.get("text", ""),
                    "score": hit.score,
                    "filing_id": hit.payload.get("filing_id"),
                    "filing_type": hit.payload.get("filing_type"),
                    "filing_date": hit.payload.get("filing_date"),
                    "page_number": hit.payload.get("page_number"),
                }
                for hit in results
            ]
        except Exception as exc:
            logger.warning("filings search failed: %s", exc)
            return []

    def search_news_semantic(
        self,
        query: str,
        company_id: Optional[str] = None,
        themes: Optional[List[str]] = None,
        since_iso: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        client = self._get_client()
        if not client:
            return []
        try:
            from qdrant_client.models import (
                DatetimeRange,
                FieldCondition,
                Filter,
                MatchAny,
                MatchValue,
                Range,
            )

            must: List[Any] = []
            if company_id:
                must.append(
                    FieldCondition(key="company_id", match=MatchValue(value=str(company_id)))
                )
            if themes:
                must.append(FieldCondition(key="themes", match=MatchAny(any=themes)))
            if since_iso:
                must.append(
                    FieldCondition(
                        key="published_at",
                        range=DatetimeRange(gte=since_iso),
                    )
                )
            results = client.search(
                collection_name=COLLECTION_NEWS,
                query_vector=self._embed_text(query),
                query_filter=Filter(must=must) if must else None,
                limit=limit,
                with_payload=True,
            )
            return [
                {
                    "text": hit.payload.get("text", ""),
                    "score": hit.score,
                    "news_id": hit.payload.get("news_id"),
                    "headline": hit.payload.get("headline"),
                    "source": hit.payload.get("source"),
                    "source_url": hit.payload.get("source_url"),
                    "published_at": hit.payload.get("published_at"),
                }
                for hit in results
            ]
        except Exception as exc:
            logger.warning("news search failed: %s", exc)
            return []

    def search_transcripts(
        self,
        query: str,
        company_id: Optional[str] = None,
        speaker_role: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        client = self._get_client()
        if not client:
            return []
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            must: List[Any] = []
            if company_id:
                must.append(
                    FieldCondition(key="company_id", match=MatchValue(value=str(company_id)))
                )
            if speaker_role:
                must.append(
                    FieldCondition(key="speaker_role", match=MatchValue(value=speaker_role))
                )
            results = client.search(
                collection_name=COLLECTION_TRANSCRIPTS,
                query_vector=self._embed_text(query),
                query_filter=Filter(must=must) if must else None,
                limit=limit,
                with_payload=True,
            )
            return [
                {
                    "text": hit.payload.get("text", ""),
                    "score": hit.score,
                    "transcript_id": hit.payload.get("transcript_id"),
                    "segment_id": hit.payload.get("segment_id"),
                    "speaker_name": hit.payload.get("speaker_name"),
                    "speaker_role": hit.payload.get("speaker_role"),
                    "turn_type": hit.payload.get("turn_type"),
                    "period": hit.payload.get("period"),
                }
                for hit in results
            ]
        except Exception as exc:
            logger.warning("transcripts search failed: %s", exc)
            return []

    def search_social(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        company_id: Optional[str] = None,
        since_iso: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        client = self._get_client()
        if not client:
            return []
        try:
            from qdrant_client.models import (
                DatetimeRange,
                FieldCondition,
                Filter,
                MatchAny,
                MatchValue,
            )

            must: List[Any] = []
            if sources:
                must.append(FieldCondition(key="source", match=MatchAny(any=sources)))
            if company_id:
                must.append(
                    FieldCondition(key="company_ids", match=MatchValue(value=str(company_id)))
                )
            if since_iso:
                must.append(
                    FieldCondition(
                        key="posted_at",
                        range=DatetimeRange(gte=since_iso),
                    )
                )
            results = client.search(
                collection_name=COLLECTION_SOCIAL,
                query_vector=self._embed_text(query),
                query_filter=Filter(must=must) if must else None,
                limit=limit,
                with_payload=True,
            )
            return [
                {
                    "text": hit.payload.get("text", ""),
                    "score": hit.score,
                    "post_id": hit.payload.get("post_id"),
                    "source": hit.payload.get("source"),
                    "sentiment_label": hit.payload.get("sentiment_label"),
                    "stance_label": hit.payload.get("stance_label"),
                    "topic_id": hit.payload.get("topic_id"),
                    "posted_at": hit.payload.get("posted_at"),
                    "author_handle": hit.payload.get("author_handle"),
                }
                for hit in results
            ]
        except Exception as exc:
            logger.warning("social search failed: %s", exc)
            return []

    def search_user_upload(
        self,
        user_id,
        upload_id,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        client = self._get_client()
        if not client:
            return []
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            results = client.search(
                collection_name=COLLECTION_USER_UPLOADS,
                query_vector=self._embed_text(query),
                query_filter=Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=str(user_id))),
                        FieldCondition(key="upload_id", match=MatchValue(value=str(upload_id))),
                    ]
                ),
                limit=limit,
                with_payload=True,
            )
            return [
                {
                    "text": hit.payload.get("text", ""),
                    "score": hit.score,
                    "page_number": hit.payload.get("page_number"),
                    "slide_title": hit.payload.get("slide_title", ""),
                }
                for hit in results
            ]
        except Exception:
            return []


# --------------------------------------------------------------------------- #
#  Module-level chunker (kept here so document_processor + filing parser     #
#  share semantics).                                                         #
# --------------------------------------------------------------------------- #

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64


def _chunk_text(text: str) -> List[str]:
    words = text.split()
    if not words:
        return []
    chunks: List[str] = []
    start = 0
    step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
    while start < len(words):
        chunks.append(" ".join(words[start : start + CHUNK_SIZE]))
        start += step
    return chunks


def chunk_text(text: str) -> List[str]:
    """Public chunker used across ETL/services."""
    return _chunk_text(text)

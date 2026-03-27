"""Vector search service (Qdrant)."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from src.config import get_settings
from src.llm import get_embeddings, get_embedding_dim


class VectorService:
    """Service for semantic search over filings and user uploads."""

    def __init__(self):
        self.settings = get_settings()
        self._client = None

    def _get_client(self):
        """Lazy-init Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient

                self._client = QdrantClient(
                    url=self.settings.qdrant_url,
                    api_key=self.settings.qdrant_api_key,
                )
            except Exception:
                return None
        return self._client

    def search_company_filings(
        self,
        company_id: UUID,
        query: str,
        filing_types: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Semantic search over company filings."""
        client = self._get_client()
        if not client:
            return []

        try:
            # Generate embedding (would use OpenAI in production)
            query_embedding = self._embed_text(query)

            from qdrant_client.models import Filter, FieldCondition, MatchValue

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
                collection_name="company_filings",
                query_vector=query_embedding,
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
        except Exception:
            return []

    def search_user_upload(
        self,
        user_id: UUID,
        upload_id: UUID,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search within user-uploaded document."""
        client = self._get_client()
        if not client:
            return []

        try:
            query_embedding = self._embed_text(query)

            from qdrant_client.models import Filter, FieldCondition, MatchValue

            results = client.search(
                collection_name="user_uploads",
                query_vector=query_embedding,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=str(user_id)),
                        ),
                        FieldCondition(
                            key="upload_id",
                            match=MatchValue(value=str(upload_id)),
                        ),
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

    def _embed_text(self, text: str) -> List[float]:
        """Generate embedding using configured provider (Ollama nomic-embed-text / OpenAI)."""
        try:
            embeddings = get_embeddings()
            return embeddings.embed_query(text)
        except Exception:
            dim = get_embedding_dim()
            return [0.0] * dim  # Fallback: zero vector (search degraded)

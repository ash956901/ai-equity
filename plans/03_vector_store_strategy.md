# Vector Store Strategy – AI Equity Research Platform

## Overview

This document defines the **vector database strategy** for semantic search over filings, presentations, news, and user uploads, comparing standalone vector DBs vs pgvector, and specifying chunking, embedding, and querying patterns.

---

## Decision: Qdrant vs pgvector

### Comparison Matrix

| Criterion | Qdrant (Standalone) | pgvector (PostgreSQL Extension) |
|-----------|---------------------|----------------------------------|
| **Performance** | Optimized for vector ops; HNSW index | Good for <10M vectors; slower at scale |
| **Scalability** | Horizontal scaling, sharding | Limited by Postgres vertical scaling |
| **Operational complexity** | Separate service to manage | Single DB, simpler ops |
| **Feature richness** | Advanced filtering, hybrid search | Basic ANN, improving rapidly |
| **Cost** | Separate hosting cost | Included in Postgres cost |
| **Query flexibility** | Rich filtering on metadata | SQL-based filtering (powerful) |
| **Latency** | <50ms for most queries | 50-200ms depending on size |
| **Integration** | Separate client/API | Native SQL queries |
| **Backup/recovery** | Separate backup strategy | Part of Postgres backup |

### Recommendation: **Qdrant (Standalone)**

**Reasoning:**

1. **Scale**: Expected to handle 1M+ document chunks across 50k+ companies; Qdrant is purpose-built for this scale.
2. **Performance**: Sub-50ms latency critical for real-time chat experience; Qdrant's HNSW index outperforms pgvector at scale.
3. **Flexibility**: Need complex filtering (company_id, filing_type, date ranges, user namespaces) combined with vector search; Qdrant's payload filtering is more mature.
4. **Future-proofing**: As document corpus grows, horizontal scaling with Qdrant is straightforward; pgvector would require sharding Postgres.
5. **Hybrid search**: Qdrant supports hybrid (vector + keyword) search natively, useful for financial term precision.

**Trade-off accepted**: Slightly higher operational complexity (one more service), but manageable with Docker/K8s and cloud-managed Qdrant.

---

## Qdrant Architecture

### Collections

We'll use **three main collections** to maintain clear separation and optimize for different query patterns:

#### 1. `company_filings`

**Purpose**: All parsed text from regulatory filings, annual reports, presentations, concalls.

**Schema**:
```python
{
    "vectors": {
        "size": 1536,  # OpenAI text-embedding-3-small
        "distance": "Cosine"
    },
    "payload_schema": {
        "company_id": "uuid",
        "company_name": "keyword",
        "filing_id": "uuid",
        "filing_type": "keyword",  # Annual_Report, Quarterly_Results, etc.
        "filing_date": "datetime",
        "fiscal_year": "integer",
        "quarter": "integer",
        "page_number": "integer",
        "chunk_index": "integer",
        "text": "text",  # Original chunk text
        "created_at": "datetime"
    }
}
```

**Indexes**:
- `company_id` (for company-specific queries)
- `filing_type` (for filtering by document type)
- `filing_date` (for temporal filtering)

#### 2. `news_articles`

**Purpose**: News article embeddings for sentiment-aware search.

**Schema**:
```python
{
    "vectors": {
        "size": 1536,
        "distance": "Cosine"
    },
    "payload_schema": {
        "news_id": "uuid",
        "company_id": "uuid",  # nullable
        "company_name": "keyword",
        "headline": "text",
        "body": "text",
        "source": "keyword",
        "published_at": "datetime",
        "sentiment_score": "float",
        "sentiment_label": "keyword",
        "impact_level": "keyword",
        "tickers": ["keyword"],
        "created_at": "datetime"
    }
}
```

**Indexes**:
- `company_id`
- `published_at`
- `sentiment_label`

#### 3. `user_uploads`

**Purpose**: User-uploaded documents with strict per-user isolation.

**Schema**:
```python
{
    "vectors": {
        "size": 1536,
        "distance": "Cosine"
    },
    "payload_schema": {
        "upload_id": "uuid",
        "user_id": "uuid",
        "session_id": "uuid",
        "filename": "keyword",
        "file_type": "keyword",
        "page_number": "integer",
        "chunk_index": "integer",
        "text": "text",
        "created_at": "datetime"
    }
}
```

**Indexes**:
- `user_id` (critical for namespace isolation)
- `session_id` (for session-specific context)

---

## Chunking Strategy

### Principles

1. **Semantic coherence**: Chunks should contain complete thoughts/paragraphs.
2. **Optimal size**: 500-1000 tokens (balance between context and retrieval precision).
3. **Overlap**: 100-150 tokens to prevent loss of context at boundaries.
4. **Metadata preservation**: Every chunk carries full context (company, filing, date, page).

### Implementation

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

def chunk_document(text: str, metadata: dict) -> List[dict]:
    """
    Chunk document text with overlap and metadata.
    
    Args:
        text: Full document text
        metadata: Dict with company_id, filing_id, filing_type, etc.
    
    Returns:
        List of chunks with metadata
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,  # ~600 tokens
        chunk_overlap=100,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks = splitter.split_text(text)
    
    return [
        {
            "text": chunk,
            "metadata": {
                **metadata,
                "chunk_index": idx,
                "chunk_length": len(chunk)
            }
        }
        for idx, chunk in enumerate(chunks)
    ]
```

### Special Cases

#### Financial Tables

For extracted tables, create a **single chunk per table** with:
- Table title/context
- Column headers
- All rows in structured format
- Metadata: `is_table=True`, `table_type=P&L/BS/CF`

```python
def chunk_financial_table(df: pd.DataFrame, context: str, metadata: dict) -> dict:
    """
    Create a single searchable chunk for a financial table.
    """
    # Format table as text
    table_text = f"{context}\n\n"
    table_text += df.to_string(index=False)
    
    return {
        "text": table_text,
        "metadata": {
            **metadata,
            "is_table": True,
            "table_rows": len(df),
            "table_columns": len(df.columns)
        }
    }
```

#### Charts

For chart-extracted data, create a chunk with:
- Chart title/metric name
- Structured series data as text
- Link to chart image URI

```python
def chunk_chart_data(chart_series: List[ChartSeries], metadata: dict) -> dict:
    """
    Create searchable chunk for chart data.
    """
    metric_name = chart_series[0].metric_name
    
    text = f"Chart: {metric_name}\n\n"
    for series in chart_series:
        text += f"{series.label}: {series.value} {series.unit}\n"
    
    return {
        "text": text,
        "metadata": {
            **metadata,
            "is_chart": True,
            "chart_image_uri": chart_series[0].chart_image_uri,
            "metric_name": metric_name
        }
    }
```

---

## Embedding Strategy

### Model Selection

**Primary**: OpenAI `text-embedding-3-small`
- **Dimensions**: 1536
- **Cost**: $0.02 / 1M tokens (very affordable)
- **Performance**: State-of-art retrieval quality
- **Latency**: ~100ms for batch of 100 chunks

**Fallback/Alternative**: Cohere `embed-english-v3.0` or open-source models (e.g., `bge-large-en-v1.5`)

### Batch Processing

```python
import openai
from typing import List

def embed_chunks(chunks: List[str], batch_size: int = 100) -> List[List[float]]:
    """
    Generate embeddings in batches for efficiency.
    
    Args:
        chunks: List of text chunks
        batch_size: Number of chunks per API call
    
    Returns:
        List of embedding vectors
    """
    embeddings = []
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=batch
        )
        
        batch_embeddings = [item.embedding for item in response.data]
        embeddings.extend(batch_embeddings)
    
    return embeddings
```

### Embedding Pipeline (Celery Task)

```python
@celery.task
def embed_and_store_filing(filing_id: UUID):
    """
    Complete embedding pipeline for a filing.
    """
    # 1. Load filing and parsed text
    filing = db.query(Filing).get(filing_id)
    parsed_data = download_json_from_s3(filing.parsed_text_uri)
    
    # 2. Chunk all pages
    all_chunks = []
    for page in parsed_data['pages']:
        page_chunks = chunk_document(
            text=page['text'],
            metadata={
                'company_id': str(filing.company_id),
                'filing_id': str(filing.id),
                'filing_type': filing.filing_type,
                'filing_date': filing.filing_date.isoformat(),
                'fiscal_year': extract_fiscal_year(filing),
                'quarter': extract_quarter(filing),
                'page_number': page['page_number']
            }
        )
        all_chunks.extend(page_chunks)
    
    # 3. Generate embeddings
    texts = [chunk['text'] for chunk in all_chunks]
    embeddings = embed_chunks(texts)
    
    # 4. Upsert to Qdrant
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct
    
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                **chunk['metadata'],
                'text': chunk['text']
            }
        )
        for chunk, embedding in zip(all_chunks, embeddings)
    ]
    
    client.upsert(
        collection_name='company_filings',
        points=points
    )
    
    # 5. Update filing status
    filing.status = 'embedded'
    db.commit()
    
    logger.info(f"Embedded {len(points)} chunks for filing {filing_id}")
```

---

## Query Patterns

### 1. Company-Specific Semantic Search

**Use case**: "What is TCS's AI strategy?"

```python
def search_company_filings(
    company_id: UUID,
    query: str,
    filing_types: List[str] = None,
    date_range: tuple = None,
    limit: int = 10
) -> List[dict]:
    """
    Search filings for a specific company.
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
    
    # Build filter
    conditions = [
        FieldCondition(
            key="company_id",
            match=MatchValue(value=str(company_id))
        )
    ]
    
    if filing_types:
        conditions.append(
            FieldCondition(
                key="filing_type",
                match=MatchValue(any=filing_types)
            )
        )
    
    if date_range:
        conditions.append(
            FieldCondition(
                key="filing_date",
                range=Range(
                    gte=date_range[0].isoformat(),
                    lte=date_range[1].isoformat()
                )
            )
        )
    
    # Generate query embedding
    query_embedding = embed_chunks([query])[0]
    
    # Search
    results = qdrant_client.search(
        collection_name='company_filings',
        query_vector=query_embedding,
        query_filter=Filter(must=conditions),
        limit=limit,
        with_payload=True
    )
    
    return [
        {
            'text': hit.payload['text'],
            'score': hit.score,
            'filing_id': hit.payload['filing_id'],
            'filing_type': hit.payload['filing_type'],
            'filing_date': hit.payload['filing_date'],
            'page_number': hit.payload['page_number']
        }
        for hit in results
    ]
```

### 2. Multi-Company Comparison Search

**Use case**: "Compare TCS and Infosys on cloud revenue growth"

```python
def search_multiple_companies(
    company_ids: List[UUID],
    query: str,
    limit_per_company: int = 5
) -> dict:
    """
    Search across multiple companies and group results.
    """
    results_by_company = {}
    
    for company_id in company_ids:
        results = search_company_filings(
            company_id=company_id,
            query=query,
            limit=limit_per_company
        )
        results_by_company[str(company_id)] = results
    
    return results_by_company
```

### 3. Temporal Analysis

**Use case**: "How has management commentary on margins changed over time?"

```python
def search_temporal(
    company_id: UUID,
    query: str,
    quarters: List[tuple]  # [(FY, Q), ...]
) -> List[dict]:
    """
    Search specific quarters and return chronologically.
    """
    all_results = []
    
    for fy, q in quarters:
        results = qdrant_client.search(
            collection_name='company_filings',
            query_vector=embed_chunks([query])[0],
            query_filter=Filter(
                must=[
                    FieldCondition(key="company_id", match=MatchValue(value=str(company_id))),
                    FieldCondition(key="fiscal_year", match=MatchValue(value=fy)),
                    FieldCondition(key="quarter", match=MatchValue(value=q))
                ]
            ),
            limit=3
        )
        
        for hit in results:
            all_results.append({
                'text': hit.payload['text'],
                'score': hit.score,
                'fiscal_year': fy,
                'quarter': q,
                'filing_date': hit.payload['filing_date']
            })
    
    return sorted(all_results, key=lambda x: (x['fiscal_year'], x['quarter']))
```

### 4. News Sentiment Search

**Use case**: "Show me negative news about banking sector"

```python
def search_news_by_sentiment(
    query: str,
    sentiment_label: str = None,  # positive, negative, neutral
    company_ids: List[UUID] = None,
    date_range: tuple = None,
    limit: int = 20
) -> List[dict]:
    """
    Search news with sentiment filtering.
    """
    conditions = []
    
    if sentiment_label:
        conditions.append(
            FieldCondition(key="sentiment_label", match=MatchValue(value=sentiment_label))
        )
    
    if company_ids:
        conditions.append(
            FieldCondition(key="company_id", match=MatchValue(any=[str(cid) for cid in company_ids]))
        )
    
    if date_range:
        conditions.append(
            FieldCondition(
                key="published_at",
                range=Range(gte=date_range[0].isoformat(), lte=date_range[1].isoformat())
            )
        )
    
    query_embedding = embed_chunks([query])[0]
    
    results = qdrant_client.search(
        collection_name='news_articles',
        query_vector=query_embedding,
        query_filter=Filter(must=conditions) if conditions else None,
        limit=limit
    )
    
    return [
        {
            'headline': hit.payload['headline'],
            'body': hit.payload['body'],
            'score': hit.score,
            'sentiment_score': hit.payload['sentiment_score'],
            'sentiment_label': hit.payload['sentiment_label'],
            'published_at': hit.payload['published_at']
        }
        for hit in results
    ]
```

### 5. User Upload Search (Namespace Isolation)

**Use case**: User uploads a PDF and asks "What are the key risks mentioned?"

```python
def search_user_upload(
    user_id: UUID,
    upload_id: UUID,
    query: str,
    limit: int = 10
) -> List[dict]:
    """
    Search within a specific user upload with strict isolation.
    """
    query_embedding = embed_chunks([query])[0]
    
    results = qdrant_client.search(
        collection_name='user_uploads',
        query_vector=query_embedding,
        query_filter=Filter(
            must=[
                FieldCondition(key="user_id", match=MatchValue(value=str(user_id))),
                FieldCondition(key="upload_id", match=MatchValue(value=str(upload_id)))
            ]
        ),
        limit=limit
    )
    
    return [
        {
            'text': hit.payload['text'],
            'score': hit.score,
            'page_number': hit.payload['page_number']
        }
        for hit in results
    ]
```

### 6. Hybrid Search (Vector + Keyword)

**Use case**: "Find mentions of 'EBITDA margin' in recent quarterly results"

```python
def hybrid_search(
    company_id: UUID,
    semantic_query: str,
    keywords: List[str],
    filing_types: List[str] = None,
    limit: int = 10
) -> List[dict]:
    """
    Combine vector similarity with keyword matching.
    """
    # Qdrant supports hybrid search with sparse vectors or text matching
    # For now, we can do post-filtering
    
    results = search_company_filings(
        company_id=company_id,
        query=semantic_query,
        filing_types=filing_types,
        limit=limit * 2  # Over-fetch for filtering
    )
    
    # Filter by keywords
    filtered = [
        r for r in results
        if any(kw.lower() in r['text'].lower() for kw in keywords)
    ]
    
    return filtered[:limit]
```

---

## Performance Optimization

### 1. Indexing Strategy

```python
# Create HNSW index for fast ANN search
from qdrant_client.models import VectorParams, Distance, HnswConfigDiff

qdrant_client.create_collection(
    collection_name='company_filings',
    vectors_config=VectorParams(
        size=1536,
        distance=Distance.COSINE,
        hnsw_config=HnswConfigDiff(
            m=16,  # Number of edges per node
            ef_construct=100,  # Construction time accuracy
            full_scan_threshold=10000  # Switch to exact search for small datasets
        )
    )
)

# Create payload indexes for fast filtering
qdrant_client.create_payload_index(
    collection_name='company_filings',
    field_name='company_id',
    field_schema='keyword'
)

qdrant_client.create_payload_index(
    collection_name='company_filings',
    field_name='filing_date',
    field_schema='datetime'
)
```

### 2. Caching Strategy

```python
from functools import lru_cache
import hashlib

def cache_key(query: str, filters: dict) -> str:
    """Generate cache key for query."""
    key_str = f"{query}_{json.dumps(filters, sort_keys=True)}"
    return hashlib.md5(key_str.encode()).hexdigest()

@lru_cache(maxsize=1000)
def cached_search(query: str, company_id: str, filing_types: tuple = None):
    """Cache frequent queries."""
    return search_company_filings(
        company_id=UUID(company_id),
        query=query,
        filing_types=list(filing_types) if filing_types else None
    )
```

### 3. Batch Queries

```python
def batch_search(queries: List[dict]) -> List[List[dict]]:
    """
    Execute multiple searches in parallel.
    
    Args:
        queries: List of dicts with 'query', 'company_id', 'filters'
    
    Returns:
        List of result lists
    """
    from concurrent.futures import ThreadPoolExecutor
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(
                search_company_filings,
                company_id=q['company_id'],
                query=q['query'],
                **q.get('filters', {})
            )
            for q in queries
        ]
        
        results = [f.result() for f in futures]
    
    return results
```

---

## Data Lifecycle Management

### 1. Retention Policy

```python
# Delete old embeddings for deleted filings
@celery.task
def cleanup_orphaned_vectors():
    """
    Remove vector embeddings for filings that no longer exist.
    """
    # Get all filing_ids from Qdrant
    scroll_result = qdrant_client.scroll(
        collection_name='company_filings',
        limit=10000,
        with_payload=['filing_id']
    )
    
    vector_filing_ids = {point.payload['filing_id'] for point in scroll_result[0]}
    
    # Get all filing_ids from Postgres
    db_filing_ids = {str(f.id) for f in db.query(Filing.id).all()}
    
    # Delete orphaned vectors
    orphaned = vector_filing_ids - db_filing_ids
    
    if orphaned:
        qdrant_client.delete(
            collection_name='company_filings',
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="filing_id",
                        match=MatchValue(any=list(orphaned))
                    )
                ]
            )
        )
        
        logger.info(f"Deleted {len(orphaned)} orphaned vector embeddings")
```

### 2. Re-embedding Strategy

```python
@celery.task
def reembed_collection(collection_name: str, new_model: str):
    """
    Re-embed entire collection with new model (e.g., model upgrade).
    """
    # This is a heavy operation; run during low-traffic periods
    
    # 1. Create new collection with new dimensions
    new_collection = f"{collection_name}_v2"
    qdrant_client.create_collection(
        collection_name=new_collection,
        vectors_config=VectorParams(size=NEW_DIMENSION, distance=Distance.COSINE)
    )
    
    # 2. Scroll through old collection
    offset = None
    while True:
        results, offset = qdrant_client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_payload=True
        )
        
        if not results:
            break
        
        # 3. Re-embed texts
        texts = [point.payload['text'] for point in results]
        new_embeddings = embed_with_new_model(texts, new_model)
        
        # 4. Insert to new collection
        new_points = [
            PointStruct(
                id=point.id,
                vector=new_embedding,
                payload=point.payload
            )
            for point, new_embedding in zip(results, new_embeddings)
        ]
        
        qdrant_client.upsert(collection_name=new_collection, points=new_points)
    
    # 5. Swap collections (manual step after validation)
    logger.info(f"Re-embedding complete. Validate {new_collection} before swapping.")
```

---

## Monitoring & Observability

### Key Metrics

1. **Query latency**: p50, p95, p99
2. **Vector count per collection**
3. **Embedding generation rate** (chunks/sec)
4. **Cache hit rate**
5. **Failed embeddings** (track and retry)

### Logging

```python
import structlog

logger = structlog.get_logger()

def log_search_query(query: str, company_id: UUID, results_count: int, latency_ms: float):
    logger.info(
        "vector_search",
        query=query[:100],  # Truncate for privacy
        company_id=str(company_id),
        results_count=results_count,
        latency_ms=latency_ms,
        collection='company_filings'
    )
```

---

## Summary

This vector store strategy provides:

1. **Qdrant as the primary vector DB** for scale and performance
2. **Three separate collections** for filings, news, and user uploads
3. **Optimized chunking** (500-1000 tokens with overlap)
4. **OpenAI embeddings** (text-embedding-3-small) for quality
5. **Rich query patterns** supporting company-specific, temporal, sentiment, and hybrid search
6. **Strict namespace isolation** for user uploads
7. **Performance optimizations** including HNSW indexing, caching, and batch processing
8. **Data lifecycle management** for cleanup and re-embedding

This architecture scales to 1M+ document chunks and supports sub-50ms query latency for real-time chat experiences.

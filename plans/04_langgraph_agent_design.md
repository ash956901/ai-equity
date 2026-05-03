# LangGraph Agent Design – AI Equity Research Platform

> **Status (as of Round 2):** historical design document. The shipped system uses the **`deepagents>=0.4.12`** wrapper (LangGraph under the hood) instead of a hand-rolled `StateGraph`, has **11 subagents** (added `discovery`, `policy-macro`, `theme-explorer`, `transcript-analyst`, `macro-commodity`, `graph-reasoning`), enforces a 14-section structured-output Pydantic contract (`src/schemas/structured_analysis.py`), and runs Discovery's **two-pass asymmetric tagger** offline. **For the current topology, see [`/backend-ai/DEEP_AGENT_ARCHITECTURE.md`](../backend-ai/DEEP_AGENT_ARCHITECTURE.md) and [SHIPPED.md](./SHIPPED.md).** Original design retained as reference.

## Overview

This document defines the **LangGraph-based agent architecture** for query-time processing, including the state model, agent graph structure, node implementations, tool definitions, and reasoning patterns for the AI equity research platform.

---

## Design Principles

1. **Deterministic flows** – No uncontrolled loops; every state transition is explicit.
2. **Strict separation** – Tools do computation; LLMs do interpretation and synthesis.
3. **Type safety** – All state is strongly typed with Pydantic models.
4. **Composability** – Nodes are single-responsibility and reusable.
5. **Observability** – Every node logs inputs/outputs for debugging.
6. **User-aware** – Synthesis adapts to user expertise level (beginner/intermediate/advanced).

---

## State Model

### Core State Schema

```python
from typing import TypedDict, Optional, List, Dict, Any
from datetime import date
from uuid import UUID
from enum import Enum

class QueryMode(str, Enum):
    COMPANY_ANALYSIS = "company_analysis"
    COMPARISON = "comparison"
    PORTFOLIO = "portfolio"
    NEWS_SENTIMENT = "news_sentiment"
    DOC_UPLOAD = "doc_upload"
    GENERAL = "general"

class ResearchState(TypedDict):
    # Input
    user_id: UUID
    session_id: UUID
    user_query: str
    expertise_level: str  # beginner, intermediate, advanced
    
    # Routing
    query_mode: Optional[QueryMode]
    
    # Context
    company_ids: Optional[List[UUID]]
    company_names: Optional[List[str]]
    portfolio_id: Optional[UUID]
    upload_id: Optional[UUID]
    date_range: Optional[tuple[date, date]]
    
    # Intermediate data (from tools)
    financial_data: Optional[Dict[str, Any]]
    ratio_data: Optional[Dict[str, Any]]
    filing_context: Optional[List[Dict[str, Any]]]
    news_context: Optional[List[Dict[str, Any]]]
    portfolio_metrics: Optional[Dict[str, Any]]
    comparison_data: Optional[Dict[str, Any]]
    chart_data: Optional[List[Dict[str, Any]]]
    
    # Output
    final_response: Optional[str]
    sources: Optional[List[Dict[str, str]]]
    visualizations: Optional[List[str]]  # URIs to generated charts
    
    # Metadata
    error: Optional[str]
    tokens_used: Optional[int]
```

---

## Agent Graph Architecture

### High-Level Flow

```
User Query
    ↓
┌───────────────┐
│ Router Node   │  → Classify query mode & extract entities
└───────┬───────┘
        │
        ├─────────────────┬──────────────┬─────────────┬──────────────┐
        ↓                 ↓              ↓             ↓              ↓
┌──────────────┐  ┌──────────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐
│  Company     │  │  Comparison  │  │Portfolio│  │  News   │  │   Doc    │
│  Analysis    │  │    Agent     │  │  Agent  │  │Sentiment│  │ Insight  │
└──────┬───────┘  └──────┬───────┘  └────┬────┘  └────┬────┘  └────┬─────┘
       │                 │               │           │           │
       └─────────────────┴───────────────┴───────────┴───────────┘
                                 ↓
                        ┌────────────────┐
                        │  Synthesis     │  → Generate final response
                        │     Node       │     with layman explanation
                        └────────┬───────┘
                                 ↓
                          Final Response
```

### Graph Implementation

```python
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor

def build_research_graph():
    """
    Build the main query-time agent graph.
    """
    graph = StateGraph(ResearchState)
    
    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("company_analysis", company_analysis_node)
    graph.add_node("comparison", comparison_node)
    graph.add_node("portfolio", portfolio_node)
    graph.add_node("news_sentiment", news_sentiment_node)
    graph.add_node("doc_insight", doc_insight_node)
    graph.add_node("synthesis", synthesis_node)
    
    # Set entry point
    graph.set_entry_point("router")
    
    # Add conditional edges from router
    graph.add_conditional_edges(
        "router",
        route_query,
        {
            QueryMode.COMPANY_ANALYSIS: "company_analysis",
            QueryMode.COMPARISON: "comparison",
            QueryMode.PORTFOLIO: "portfolio",
            QueryMode.NEWS_SENTIMENT: "news_sentiment",
            QueryMode.DOC_UPLOAD: "doc_insight",
            QueryMode.GENERAL: "synthesis"  # Skip to synthesis for general queries
        }
    )
    
    # All specialized nodes flow to synthesis
    graph.add_edge("company_analysis", "synthesis")
    graph.add_edge("comparison", "synthesis")
    graph.add_edge("portfolio", "synthesis")
    graph.add_edge("news_sentiment", "synthesis")
    graph.add_edge("doc_insight", "synthesis")
    
    # Synthesis is the end
    graph.add_edge("synthesis", END)
    
    return graph.compile()
```

---

## Node Implementations

### 1. Router Node

**Purpose**: Classify query intent and extract entities (companies, dates, portfolio).

```python
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

router_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a query classifier for an equity research platform.
    
Classify the user query into one of these modes:
- COMPANY_ANALYSIS: Analyzing a single company's financials, strategy, risks
- COMPARISON: Comparing 2+ companies
- PORTFOLIO: Portfolio analysis, risk, allocation questions
- NEWS_SENTIMENT: Recent news, sentiment, market events
- DOC_UPLOAD: Questions about a user-uploaded document
- GENERAL: General market questions, definitions

Also extract:
- Company names/tickers mentioned
- Date ranges (if any)
- Portfolio reference (if any)

Return JSON with: mode, company_names, date_range, portfolio_mentioned"""),
    ("user", "{query}")
])

def router_node(state: ResearchState) -> ResearchState:
    """
    Route query and extract entities.
    """
    # Call LLM to classify
    chain = router_prompt | router_llm
    response = chain.invoke({"query": state["user_query"]})
    
    # Parse response (assume structured output)
    routing_data = json.loads(response.content)
    
    # Resolve company names to IDs
    company_ids = []
    if routing_data.get("company_names"):
        company_ids = resolve_company_names(routing_data["company_names"])
    
    # Resolve portfolio
    portfolio_id = None
    if routing_data.get("portfolio_mentioned"):
        portfolio_id = get_user_primary_portfolio(state["user_id"])
    
    return {
        **state,
        "query_mode": QueryMode(routing_data["mode"]),
        "company_ids": company_ids,
        "company_names": routing_data.get("company_names", []),
        "portfolio_id": portfolio_id,
        "date_range": parse_date_range(routing_data.get("date_range"))
    }

def route_query(state: ResearchState) -> QueryMode:
    """
    Conditional edge function.
    """
    return state["query_mode"]
```

### 2. Company Analysis Node

**Purpose**: Analyze a single company using financial tools and vector search.

```python
from langchain.tools import Tool

# Define tools (see Tools section below)
financial_tools = [
    get_latest_financials_tool,
    calculate_ratios_tool,
    search_filings_tool,
    get_recent_news_tool,
    get_company_themes_tool
]

def company_analysis_node(state: ResearchState) -> ResearchState:
    """
    Perform deep company analysis.
    """
    company_id = state["company_ids"][0]
    query = state["user_query"]
    
    # 1. Get latest financials
    financial_data = get_latest_financials_tool.invoke({
        "company_id": company_id,
        "periods": 4  # Last 4 quarters
    })
    
    # 2. Calculate key ratios
    ratio_data = calculate_ratios_tool.invoke({
        "company_id": company_id,
        "period": financial_data["latest_period"]
    })
    
    # 3. Search filings for query-specific context
    filing_context = search_filings_tool.invoke({
        "company_id": company_id,
        "query": query,
        "filing_types": ["Annual_Report", "Quarterly_Results", "Presentation"],
        "limit": 5
    })
    
    # 4. Get recent news
    news_context = get_recent_news_tool.invoke({
        "company_id": company_id,
        "days": 30,
        "limit": 10
    })
    
    # 5. Get theme exposure
    themes = get_company_themes_tool.invoke({
        "company_id": company_id
    })
    
    # 6. Detect risk flags
    risk_flags = detect_risk_flags_tool.invoke({
        "company_id": company_id,
        "financial_data": financial_data
    })
    
    return {
        **state,
        "financial_data": financial_data,
        "ratio_data": ratio_data,
        "filing_context": filing_context,
        "news_context": news_context,
        "comparison_data": {
            "themes": themes,
            "risk_flags": risk_flags
        }
    }
```

### 3. Comparison Node

**Purpose**: Compare multiple companies across standard metrics.

```python
def comparison_node(state: ResearchState) -> ResearchState:
    """
    Compare 2+ companies.
    """
    company_ids = state["company_ids"]
    query = state["user_query"]
    
    # 1. Get financials for all companies
    all_financials = {}
    all_ratios = {}
    
    for company_id in company_ids:
        all_financials[str(company_id)] = get_latest_financials_tool.invoke({
            "company_id": company_id,
            "periods": 4
        })
        
        all_ratios[str(company_id)] = calculate_ratios_tool.invoke({
            "company_id": company_id,
            "period": all_financials[str(company_id)]["latest_period"]
        })
    
    # 2. Search filings for comparison context
    filing_context = []
    for company_id in company_ids:
        results = search_filings_tool.invoke({
            "company_id": company_id,
            "query": query,
            "limit": 3
        })
        filing_context.extend(results)
    
    # 3. Build comparison matrix
    comparison_matrix = build_comparison_matrix_tool.invoke({
        "company_ids": company_ids,
        "financials": all_financials,
        "ratios": all_ratios,
        "dimensions": ["growth", "profitability", "leverage", "valuation", "risk"]
    })
    
    return {
        **state,
        "financial_data": all_financials,
        "ratio_data": all_ratios,
        "filing_context": filing_context,
        "comparison_data": comparison_matrix
    }
```

### 4. Portfolio Node

**Purpose**: Analyze user portfolio for risk, allocation, and performance.

```python
def portfolio_node(state: ResearchState) -> ResearchState:
    """
    Analyze portfolio.
    """
    portfolio_id = state["portfolio_id"]
    query = state["user_query"]
    
    # 1. Get holdings
    holdings = get_portfolio_holdings_tool.invoke({
        "portfolio_id": portfolio_id
    })
    
    # 2. Calculate portfolio metrics
    portfolio_metrics = calculate_portfolio_metrics_tool.invoke({
        "portfolio_id": portfolio_id
    })
    
    # 3. Identify concentration risks
    concentration_analysis = analyze_concentration_tool.invoke({
        "holdings": holdings
    })
    
    # 4. Get news for portfolio companies
    portfolio_company_ids = [h["company_id"] for h in holdings]
    news_context = []
    
    for company_id in portfolio_company_ids[:10]:  # Limit to top 10 holdings
        news = get_recent_news_tool.invoke({
            "company_id": company_id,
            "days": 7,
            "limit": 3
        })
        news_context.extend(news)
    
    # 5. Check for red flags in holdings
    risk_flags = []
    for company_id in portfolio_company_ids:
        flags = detect_risk_flags_tool.invoke({"company_id": company_id})
        if flags:
            risk_flags.append({"company_id": company_id, "flags": flags})
    
    return {
        **state,
        "portfolio_metrics": {
            **portfolio_metrics,
            "concentration": concentration_analysis,
            "risk_flags": risk_flags
        },
        "news_context": news_context
    }
```

### 5. News Sentiment Node

**Purpose**: Analyze recent news and sentiment for companies or sectors.

```python
def news_sentiment_node(state: ResearchState) -> ResearchState:
    """
    Analyze news sentiment.
    """
    company_ids = state.get("company_ids", [])
    query = state["user_query"]
    
    # 1. Search news semantically
    news_results = search_news_semantic_tool.invoke({
        "query": query,
        "company_ids": company_ids if company_ids else None,
        "days": 30,
        "limit": 20
    })
    
    # 2. Aggregate sentiment
    sentiment_summary = aggregate_sentiment_tool.invoke({
        "news_articles": news_results
    })
    
    # 3. Identify key themes in news
    news_themes = extract_news_themes_tool.invoke({
        "news_articles": news_results
    })
    
    return {
        **state,
        "news_context": news_results,
        "comparison_data": {
            "sentiment_summary": sentiment_summary,
            "news_themes": news_themes
        }
    }
```

### 6. Doc Insight Node

**Purpose**: Analyze user-uploaded documents.

```python
def doc_insight_node(state: ResearchState) -> ResearchState:
    """
    Analyze uploaded document.
    """
    upload_id = state["upload_id"]
    user_id = state["user_id"]
    query = state["user_query"]
    
    # 1. Search within uploaded document
    doc_context = search_user_upload_tool.invoke({
        "user_id": user_id,
        "upload_id": upload_id,
        "query": query,
        "limit": 10
    })
    
    # 2. Get document metadata
    upload_meta = get_upload_metadata_tool.invoke({
        "upload_id": upload_id
    })
    
    # 3. Extract key insights (if financial doc)
    if upload_meta["file_type"] in ["pdf", "pptx"]:
        insights = extract_document_insights_tool.invoke({
            "upload_id": upload_id,
            "focus": query
        })
    else:
        insights = None
    
    return {
        **state,
        "filing_context": doc_context,
        "comparison_data": {
            "upload_meta": upload_meta,
            "insights": insights
        }
    }
```

### 7. Synthesis Node

**Purpose**: Generate final response with domain reasoning and layman explanation.

```python
from langchain.prompts import ChatPromptTemplate

synthesis_llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

synthesis_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a senior buy-side equity research analyst.

Generate a comprehensive response that:
1. Answers the user's question directly
2. Provides domain-aware reasoning (identify sectors, subdomains, second-order effects)
3. Classifies positive/negative impacts
4. Cites specific data points and sources
5. Includes an "Explained Simply" section for {expertise_level} users

Structure:
## Analysis
[Technical analysis with data]

## Key Insights
- Insight 1
- Insight 2

## Risk Factors / Opportunities
[Balanced view]

## Explained Simply
[Layman explanation]

## Sources
[List sources with links]

Use the provided context data. Never make up numbers."""),
    ("user", """User Query: {query}

Context Data:
Financial Data: {financial_data}
Ratio Data: {ratio_data}
Filing Context: {filing_context}
News Context: {news_context}
Portfolio Metrics: {portfolio_metrics}
Comparison Data: {comparison_data}

Generate response:""")
])

def synthesis_node(state: ResearchState) -> ResearchState:
    """
    Synthesize final response.
    """
    # Prepare context
    context = {
        "query": state["user_query"],
        "expertise_level": state["expertise_level"],
        "financial_data": json.dumps(state.get("financial_data", {}), indent=2),
        "ratio_data": json.dumps(state.get("ratio_data", {}), indent=2),
        "filing_context": json.dumps(state.get("filing_context", [])[:5], indent=2),
        "news_context": json.dumps(state.get("news_context", [])[:10], indent=2),
        "portfolio_metrics": json.dumps(state.get("portfolio_metrics", {}), indent=2),
        "comparison_data": json.dumps(state.get("comparison_data", {}), indent=2)
    }
    
    # Generate response
    chain = synthesis_prompt | synthesis_llm
    response = chain.invoke(context)
    
    # Extract sources
    sources = extract_sources_from_context(state)
    
    return {
        **state,
        "final_response": response.content,
        "sources": sources,
        "tokens_used": response.response_metadata.get("token_usage", {}).get("total_tokens")
    }

def extract_sources_from_context(state: ResearchState) -> List[Dict[str, str]]:
    """
    Extract source citations from context.
    """
    sources = []
    
    # From filings
    if state.get("filing_context"):
        for filing in state["filing_context"][:5]:
            sources.append({
                "type": "filing",
                "title": filing.get("filing_type", "Document"),
                "date": filing.get("filing_date", ""),
                "url": filing.get("source_url", "")
            })
    
    # From news
    if state.get("news_context"):
        for news in state["news_context"][:5]:
            sources.append({
                "type": "news",
                "title": news.get("headline", ""),
                "date": news.get("published_at", ""),
                "url": news.get("source_url", "")
            })
    
    return sources
```

---

## Tool Definitions

### Financial Tools

```python
from langchain.tools import tool

@tool
def get_latest_financials_tool(company_id: UUID, periods: int = 4) -> dict:
    """
    Get latest financial statements for a company.
    
    Args:
        company_id: Company UUID
        periods: Number of recent periods to fetch
    
    Returns:
        Dict with P&L, Balance Sheet, Cash Flow data
    """
    from app.services.financial_service import FinancialService
    
    service = FinancialService()
    return service.get_latest_financials(company_id, periods)

@tool
def calculate_ratios_tool(company_id: UUID, period: date) -> dict:
    """
    Calculate financial ratios for a company at a specific period.
    
    Args:
        company_id: Company UUID
        period: Period end date
    
    Returns:
        Dict with profitability, leverage, liquidity, efficiency ratios
    """
    from app.services.financial_service import FinancialService
    
    service = FinancialService()
    return service.calculate_ratios(company_id, period)

@tool
def detect_risk_flags_tool(company_id: UUID, financial_data: dict = None) -> List[dict]:
    """
    Detect financial red flags.
    
    Args:
        company_id: Company UUID
        financial_data: Optional pre-fetched financial data
    
    Returns:
        List of risk flags with severity and description
    """
    from app.services.risk_service import RiskService
    
    service = RiskService()
    return service.detect_risk_flags(company_id, financial_data)
```

### Vector Search Tools

```python
@tool
def search_filings_tool(
    company_id: UUID,
    query: str,
    filing_types: List[str] = None,
    limit: int = 5
) -> List[dict]:
    """
    Semantic search over company filings.
    
    Args:
        company_id: Company UUID
        query: Search query
        filing_types: Filter by filing types
        limit: Max results
    
    Returns:
        List of relevant filing chunks with metadata
    """
    from app.services.vector_service import VectorService
    
    service = VectorService()
    return service.search_company_filings(
        company_id=company_id,
        query=query,
        filing_types=filing_types,
        limit=limit
    )

@tool
def search_user_upload_tool(
    user_id: UUID,
    upload_id: UUID,
    query: str,
    limit: int = 10
) -> List[dict]:
    """
    Search within user-uploaded document.
    
    Args:
        user_id: User UUID (for namespace isolation)
        upload_id: Upload UUID
        query: Search query
        limit: Max results
    
    Returns:
        List of relevant chunks from uploaded document
    """
    from app.services.vector_service import VectorService
    
    service = VectorService()
    return service.search_user_upload(
        user_id=user_id,
        upload_id=upload_id,
        query=query,
        limit=limit
    )
```

### News Tools

```python
@tool
def get_recent_news_tool(
    company_id: UUID,
    days: int = 30,
    limit: int = 10
) -> List[dict]:
    """
    Get recent news for a company.
    
    Args:
        company_id: Company UUID
        days: Look back period
        limit: Max articles
    
    Returns:
        List of news articles with sentiment
    """
    from app.services.news_service import NewsService
    
    service = NewsService()
    return service.get_recent_news(company_id, days, limit)

@tool
def search_news_semantic_tool(
    query: str,
    company_ids: List[UUID] = None,
    days: int = 30,
    limit: int = 20
) -> List[dict]:
    """
    Semantic search over news articles.
    
    Args:
        query: Search query
        company_ids: Filter by companies
        days: Look back period
        limit: Max results
    
    Returns:
        List of relevant news articles
    """
    from app.services.vector_service import VectorService
    
    service = VectorService()
    return service.search_news(
        query=query,
        company_ids=company_ids,
        days=days,
        limit=limit
    )

@tool
def aggregate_sentiment_tool(news_articles: List[dict]) -> dict:
    """
    Aggregate sentiment across multiple news articles.
    
    Args:
        news_articles: List of news articles with sentiment scores
    
    Returns:
        Dict with overall sentiment, distribution, key themes
    """
    from app.services.news_service import NewsService
    
    service = NewsService()
    return service.aggregate_sentiment(news_articles)
```

### Portfolio Tools

```python
@tool
def get_portfolio_holdings_tool(portfolio_id: UUID) -> List[dict]:
    """
    Get current holdings in a portfolio.
    
    Args:
        portfolio_id: Portfolio UUID
    
    Returns:
        List of holdings with company info, quantity, value
    """
    from app.services.portfolio_service import PortfolioService
    
    service = PortfolioService()
    return service.get_holdings(portfolio_id)

@tool
def calculate_portfolio_metrics_tool(portfolio_id: UUID) -> dict:
    """
    Calculate portfolio-level metrics.
    
    Args:
        portfolio_id: Portfolio UUID
    
    Returns:
        Dict with allocation, concentration, risk, performance metrics
    """
    from app.services.portfolio_service import PortfolioService
    
    service = PortfolioService()
    return service.calculate_metrics(portfolio_id)

@tool
def analyze_concentration_tool(holdings: List[dict]) -> dict:
    """
    Analyze concentration risk in portfolio.
    
    Args:
        holdings: List of holdings
    
    Returns:
        Dict with concentration metrics, risk scores
    """
    from app.services.risk_service import RiskService
    
    service = RiskService()
    return service.analyze_concentration(holdings)
```

### Comparison Tools

```python
@tool
def build_comparison_matrix_tool(
    company_ids: List[UUID],
    financials: dict,
    ratios: dict,
    dimensions: List[str]
) -> dict:
    """
    Build structured comparison matrix across companies.
    
    Args:
        company_ids: List of company UUIDs
        financials: Financial data for all companies
        ratios: Ratio data for all companies
        dimensions: Dimensions to compare (growth, profitability, etc.)
    
    Returns:
        Structured comparison matrix
    """
    from app.services.comparison_service import ComparisonService
    
    service = ComparisonService()
    return service.build_matrix(company_ids, financials, ratios, dimensions)
```

### Theme Tools

```python
@tool
def get_company_themes_tool(company_id: UUID) -> List[dict]:
    """
    Get theme exposure for a company.
    
    Args:
        company_id: Company UUID
    
    Returns:
        List of themes with exposure type, confidence, impact scores
    """
    from app.services.discovery_service import DiscoveryService
    
    service = DiscoveryService()
    return service.get_company_themes(company_id)
```

---

## Memory Integration

### Conversation Memory

```python
from langchain.memory import ConversationBufferMemory

def get_session_memory(session_id: UUID) -> ConversationBufferMemory:
    """
    Get or create memory for a chat session.
    """
    # Check Redis cache
    cached_memory = redis_client.get(f"session:{session_id}:memory")
    
    if cached_memory:
        return ConversationBufferMemory.from_json(cached_memory)
    
    # Load from DB
    messages = db.query(ChatMessage).filter_by(
        session_id=session_id
    ).order_by(ChatMessage.created_at).all()
    
    memory = ConversationBufferMemory()
    for msg in messages:
        if msg.role == "user":
            memory.chat_memory.add_user_message(msg.content)
        elif msg.role == "assistant":
            memory.chat_memory.add_ai_message(msg.content)
    
    # Cache in Redis
    redis_client.setex(
        f"session:{session_id}:memory",
        3600,  # 1 hour TTL
        memory.to_json()
    )
    
    return memory

def update_session_memory(session_id: UUID, user_msg: str, assistant_msg: str):
    """
    Update session memory after interaction.
    """
    memory = get_session_memory(session_id)
    memory.chat_memory.add_user_message(user_msg)
    memory.chat_memory.add_ai_message(assistant_msg)
    
    # Save to Redis
    redis_client.setex(
        f"session:{session_id}:memory",
        3600,
        memory.to_json()
    )
    
    # Save to DB
    db.add(ChatMessage(session_id=session_id, role="user", content=user_msg))
    db.add(ChatMessage(session_id=session_id, role="assistant", content=assistant_msg))
    db.commit()
```

---

## Execution Example

### FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Compile graph once at startup
research_graph = build_research_graph()

class QueryRequest(BaseModel):
    user_id: UUID
    session_id: UUID
    query: str

class QueryResponse(BaseModel):
    response: str
    sources: List[dict]
    visualizations: List[str]
    tokens_used: int

@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process user query through agent graph.
    """
    # Get user profile
    user = db.query(User).get(request.user_id)
    
    # Initialize state
    initial_state = ResearchState(
        user_id=request.user_id,
        session_id=request.session_id,
        user_query=request.query,
        expertise_level=user.expertise_level
    )
    
    try:
        # Execute graph
        final_state = research_graph.invoke(initial_state)
        
        # Update memory
        update_session_memory(
            session_id=request.session_id,
            user_msg=request.query,
            assistant_msg=final_state["final_response"]
        )
        
        return QueryResponse(
            response=final_state["final_response"],
            sources=final_state.get("sources", []),
            visualizations=final_state.get("visualizations", []),
            tokens_used=final_state.get("tokens_used", 0)
        )
    
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Monitoring & Observability

### Logging

```python
import structlog

logger = structlog.get_logger()

def log_node_execution(node_name: str, state: ResearchState, duration_ms: float):
    """
    Log node execution for observability.
    """
    logger.info(
        "node_executed",
        node=node_name,
        user_id=str(state["user_id"]),
        session_id=str(state["session_id"]),
        query_mode=state.get("query_mode"),
        duration_ms=duration_ms,
        has_error=state.get("error") is not None
    )
```

### Metrics

Track:
1. **Query latency** by mode (p50, p95, p99)
2. **Tool call counts** per query
3. **Token usage** per query
4. **Error rates** by node
5. **Cache hit rates** for tools

---

## Summary

This LangGraph design provides:

1. **Deterministic agent graph** with explicit state transitions
2. **Specialized nodes** for analysis, comparison, portfolio, news, and doc insights
3. **Strict tool/LLM separation** – tools compute, LLMs interpret
4. **Type-safe state** with Pydantic models
5. **User-aware synthesis** adapting to expertise level
6. **Comprehensive tool library** for financial, vector, news, and portfolio operations
7. **Memory integration** for conversational context
8. **Production-ready** FastAPI integration with monitoring

This architecture scales to handle complex multi-turn conversations while maintaining deterministic, auditable reasoning flows.

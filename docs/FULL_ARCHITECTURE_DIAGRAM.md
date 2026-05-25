# Full System Architecture Diagrams

You can copy the code blocks below and paste them directly into the [Mermaid Live Editor](https://mermaid.live/) (or any markdown viewer that supports Mermaid, like GitHub or Notion) to render the full system diagrams.

## 1. High-Level Full System Architecture (Frontend + Backend + Data)

This diagram shows the complete bird's-eye view of the system, from the React frontend down to the external APIs and data storage.

```mermaid
graph TD
    %% Styling
    classDef frontend fill:#3b82f6,stroke:#1d4ed8,stroke-width:2px,color:#fff;
    classDef backend fill:#10b981,stroke:#047857,stroke-width:2px,color:#fff;
    classDef agents fill:#8b5cf6,stroke:#4338ca,stroke-width:2px,color:#fff;
    classDef etl fill:#f59e0b,stroke:#b45309,stroke-width:2px,color:#fff;
    classDef db fill:#6366f1,stroke:#4f46e5,stroke-width:2px,color:#fff;
    classDef external fill:#6b7280,stroke:#374151,stroke-width:2px,color:#fff;

    %% FRONTEND LAYER
    subgraph FrontendLayer ["Frontend Application (React / Vite)"]
        direction TB
        UI[App Shell & Command Palette]:::frontend
        subgraph Workspaces ["Feature Workspaces"]
            direction LR
            DB[Dashboard]:::frontend
            PF[Portfolio]:::frontend
            CP[Compare]:::frontend
            CA[Company Analysis]:::frontend
            TH[Thematic Discovery]:::frontend
            FL[Filings & Docs]:::frontend
        end
        UI --> Workspaces
    end

    %% API LAYER
    subgraph APILayer ["Backend API (FastAPI)"]
        Router[REST Endpoints]:::backend
        Middleware[Auth & Rate Limiting]:::backend
        Router --> Middleware
    end

    %% AGENT LAYER
    subgraph AgentLayer ["AI Agent Engine (DeepAgents / LangGraph)"]
        Iris[Iris Orchestrator]:::agents
        subgraph SubAgents ["Specialist Sub-Agents"]
            direction LR
            SA1[Company]:::agents
            SA2[Compare]:::agents
            SA3[Portfolio]:::agents
            SA4[News]:::agents
            SA5[DocInsight]:::agents
            SA6[Thematic]:::agents
            SA7[Causal Detective]:::agents
        end
        Iris --> |Delegates Task| SubAgents
    end

    %% ETL & BACKGROUND WORKERS
    subgraph ETLLayer ["Background Workers (Celery & Redis)"]
        Beat[Celery Beat Scheduler]:::etl
        Workers[Celery Workers]:::etl
        Beat --> |Triggers| Workers
        subgraph Pipelines ["Data Pipelines"]
            direction LR
            P1[Filing Crawlers]:::etl
            P2[News Sync]:::etl
            P3[Event Monitor]:::etl
            P4[Doc Processor]:::etl
        end
        Workers --> Pipelines
    end

    %% DATA STORAGE LAYER
    subgraph DataLayer ["Data Storage"]
        direction LR
        PG[(PostgreSQL\nRelational Data)]:::db
        QD[(Qdrant\nVector Embeddings)]:::db
        RD[(Redis\nCache & Broker)]:::db
        S3[(AWS S3\nRaw Documents)]:::db
    end

    %% EXTERNAL APIS
    subgraph ExternalLayer ["External Services"]
        direction LR
        Ex1[NSE / BSE / IR Sites]:::external
        Ex2[News / GDELT / OilPrice]:::external
        LLM[LLMs: GPT-4o / Groq]:::external
    end

    %% RELATIONSHIPS
    Workspaces --> |HTTP / REST| Router
    Middleware --> Iris
    
    SubAgents --> |Tool Calls: SQL| PG
    SubAgents --> |Tool Calls: Semantic Search| QD
    SubAgents --> |Reasoning| LLM
    
    Pipelines --> |Store Metadata| PG
    Pipelines --> |Store Chunks| QD
    Pipelines --> |Upload PDF/PPT| S3
    Pipelines --> |Summarize & Extract| LLM
    
    P1 --> Ex1
    P2 --> Ex2
    P3 --> Ex2
```

---

## 2. Detailed Data Flow: ETL & RAG Pipeline

This diagram zooms in on exactly how a raw document from the internet turns into an AI answer on the frontend.

```mermaid
graph TD
    %% Styling
    classDef step fill:#14b8a6,stroke:#047857,stroke-width:2px,color:#fff;
    classDef llm fill:#8b5cf6,stroke:#4c1d95,stroke-width:2px,color:#fff;
    classDef db fill:#6366f1,stroke:#3730a3,stroke-width:2px,color:#fff;

    subgraph Phase1_Ingestion ["Phase 1: Ingestion (Async)"]
        direction TB
        Src[Raw Document\nNSE/BSE PDF] --> C[Crawler Service]:::step
        C --> D[Document Processor\nPyMuPDF / pdfplumber]:::step
        D --> T[Text Cleaner & Normalizer]:::step
        T --> CH[Semantic Chunker\n500 tokens + overlap]:::step
    end

    subgraph Phase2_Enrichment ["Phase 2: LLM Enrichment & Embedding"]
        direction TB
        CH --> E[Embedding Generator\nnomic-embed-text]:::step
        CH --> EN[Filing Enricher]:::step
        EN --> |Extract| L1{LLM Extract:\nSummary, Red Flags,\nMetrics}:::llm
    end

    subgraph Phase3_Storage ["Phase 3: Storage"]
        direction LR
        E --> |Vectors| Q[(Qdrant Vector DB)]:::db
        L1 --> |Structured JSON| P[(PostgreSQL)]:::db
    end

    subgraph Phase4_Retrieval ["Phase 4: Retrieval Augmented Generation (RAG)"]
        direction TB
        U[User Query] --> R[Iris Agent]:::llm
        R --> S[Specialist Agent\ne.g., DocInsight]:::llm
        S --> |Tool Call: search_filings| Q
        S --> |Tool Call: get_financials| P
        Q --> |Relevant Chunks| S
        P --> |Financial Ratios| S
        S --> |Synthesize| Ans[Final Grounded Answer]:::step
    end

    Phase1_Ingestion --> Phase2_Enrichment
    Phase2_Enrichment --> Phase3_Storage
```

---

## 3. Causal Intelligence Engine Flow

This diagram specifically highlights how the "Hidden Patterns" engine works.

```mermaid
graph LR
    %% Styling
    classDef external fill:#6b7280,stroke:#374151,stroke-width:2px,color:#fff;
    classDef process fill:#f59e0b,stroke:#b45309,stroke-width:2px,color:#fff;
    classDef db fill:#6366f1,stroke:#3730a3,stroke-width:2px,color:#fff;
    classDef insight fill:#10b981,stroke:#047857,stroke-width:2px,color:#fff;

    E1[GDELT Cloud]:::external --> |Geopolitical Events| M1[Event Monitor Task]:::process
    E2[OilPrice / Commodity API]:::external --> |Price Spikes| M2[Commodity Sync Task]:::process
    E3[News APIs]:::external --> |Classified News| M3[News Classifier Task]:::process

    M1 --> DB[(PostgreSQL)]:::db
    M2 --> DB
    M3 --> DB

    DB --> CC{Causal Chain Engine}:::process
    
    CC --> |Trigger: Middle East Conflict| H1[Hop 1: Oil Prices Surge]:::process
    H1 --> |Hop 2: Input Cost Increase| H2[Hop 2: Aviation Sector]:::process
    H2 --> |Hop 3: Margin Pressure| H3[Hop 3: Airline Stocks]:::process

    H3 --> I[Portfolio Alerts & Hidden Pattern UI]:::insight
```
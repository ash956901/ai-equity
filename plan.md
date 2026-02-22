# Project Plan: AI-Native Equity Research Platform

## 1. Project Overview
A unified, AI-driven platform designed to democratize institutional-grade equity research for retail investors. The system leverages Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), and Semantic Knowledge Graphs to synthesize vast amounts of unstructured financial data into actionable, real-time intelligence.


## 2. Core Features & Tech Stack

### 2.1 Multi-Dimensional Data Ingestion Layer
* **Goal:** Scrape, parse, and structure diverse financial documents beyond standard PDFs.
* **Data Sources:** Quarterly/Annual PDF releases, Investor Presentations (PPTs), Concall Transcripts, Company Releases, Stock Notifications, and Board Meeting decks.
* **Tech:** Python, `BeautifulSoup`/`Selenium` (for exchange scraping), `pdfplumber` (for text), `python-pptx` & OCR (for scanning investor presentation slides and charts).

### 2.2 N-th Order Thematic Discovery & Sentiment Engine
* **Goal:** Analyze news sentiment and map its "ripple effects" across interconnected industries (e.g., A government push for Ethanol positively impacts the Petroleum sector directly, and the Sugar industry indirectly as a byproduct).
* **How:** * Use FinBERT or LangChain-orchestrated LLMs for real-time news sentiment classification (Bullish/Bearish/Neutral).
    * Construct a lightweight Semantic Knowledge Graph to map entity relationships (Multi-hop reasoning).
* **Tech:** Hugging Face (FinBERT), LangChain, NetworkX (for graph logic), Pinecone (Vector DB).

### 2.3 Conversational AI ("Iris" Deep Research Assistant)
* **Goal:** A domain-specific chatbot for querying financial data grounded strictly in uploaded documents to minimize hallucination.
* **How:** Implement an advanced RAG pipeline with strict context windowing.
* **Tech:** FastAPI (Backend), OpenAI/Open-source base models (Llama 3 / GPT-4o).

### 2.4 Portfolio Intelligence & Automated Timeline
* **Goal:** Calculate risk metrics (PE/PB, volatility) and provide a scrolling feed of <50-word actionable insights from daily filings.
* **Tech:** Python (Pandas, NumPy) for quantitative processing, React.js/Next.js for real-time WebSocket dashboard rendering.

---

## 3. Project Execution Plan (12-Week Roadmap)

### Phase 1: Planning & System Design (Weeks 1-2)
* [ ] Finalize system architecture and data pipelines.
* [ ] Set up GitHub repository with `.github/copilot-instructions.md` for team coding standards.
* [ ] Define evaluation metrics (RAG accuracy, latency, retrieval precision).

### Phase 2: Data Ingestion & Preprocessing Setup (Weeks 3-4)
* [ ] Develop automated scraping scripts for NSE/BSE filings, news feeds, and investor presentations.
* [ ] Implement document parsing (PDF text extraction, OCR for charts/PPTs).
* [ ] Configure text chunking and embedding pipelines using local Hugging Face models.

### Phase 3: AI Engine & RAG Implementation (Weeks 5-7)
* [ ] Deploy Vector Database (Pinecone) for document indexing.
* [ ] Build the core RAG pipeline using LangChain/LlamaIndex.
* [ ] Implement the Knowledge Graph logic for *Second-Order Effect* thematic tagging.
* [ ] Develop the "Iris" conversational agent for financial context handling.

### Phase 4: Analytics Orchestration & UI Development (Weeks 8-9)
* [ ] Build quantitative analytics engine using Pandas for portfolio intelligence.
* [ ] Develop the Next.js frontend and integrate with backend REST/WebSocket APIs.
* [ ] Set up real-time dashboards for the Automated Timeline and News Sentiment tracker.

### Phase 5: System Testing & Evaluation (Weeks 10-11)
* [ ] Execute controlled testing on discovery accuracy and N-th order thematic tagging.
* [ ] Collect latency and generation accuracy metrics (aiming for >90% factual retrieval).
* [ ] Stress-test system behavior under heavy query loads.

### Phase 6: Analysis, Documentation & Finalization (Week 12)
* [ ] Perform statistical analysis of AI retrieval results.
* [ ] Finalize Project Report, PPT preparation, and defense rehearsal.
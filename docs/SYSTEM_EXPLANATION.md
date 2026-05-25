# AI Equity Research Platform - A Simple Guide

This document provides a simple, high-level explanation of how the AI Equity Research Platform works. Think of this system as an autonomous, tireless team of financial analysts that constantly reads the news, analyzes complex financial documents, tracks global events, and answers your investment questions.

The system is divided into three main parts:
1. **The Data Gatherer (ETL System)**
2. **The AI Brain (Agent Architecture)**
3. **The Hidden Pattern Finder (Causal Intelligence)**

---

## 1. The Data Gatherer (ETL System)

**ETL** stands for Extract, Transform, and Load. This is the pipeline that feeds information into the AI. It works in the background 24/7 to ensure the AI always has the latest data.

### The "Extract" Phase (The Crawlers)
The system has several automated "bots" (crawlers) that scour the internet for data:
*   **Exchange Bots:** They constantly watch the NSE (National Stock Exchange) and BSE (Bombay Stock Exchange) for new corporate announcements and filings.
*   **Investor Relations Bots:** If a company posts a new presentation on their own website, this bot automatically finds it and downloads it.
*   **News Bots:** They read financial news articles and use AI to decide if the news is good (bullish) or bad (bearish) for specific companies or sectors.
*   **Global Monitors:** They track the prices of commodities (like Oil, Gold, Natural Gas) and watch for major geopolitical events (like conflicts or trade tensions).

### The "Transform & Load" Phase (Document Processing)
When the system downloads a big PDF (like an Annual Report), it doesn't just save the file. It actively reads it:
*   **Reading:** It extracts all the text, tables, and even charts (using AI vision) from the document.
*   **Cleaning:** It removes messy formatting, headers, and footers.
*   **Chunking & Embedding:** It breaks the document down into smaller, logical sections (like paragraphs or chapters). It then converts these sections into a mathematical format called "vector embeddings." This allows the AI to search the document by *meaning*, not just by exact keywords.
*   **Enrichment:** A fast AI quickly scans the document to pull out a short summary, flag any major risks (red flags), and extract key financial numbers.
*   **Loading:** Finally, all this searchable data is loaded into a specialized database (Qdrant) so the AI Brain can instantly recall it later.

---

## 2. The AI Brain (Agent Architecture)

When you ask the system a question, you aren't just talking to one generic AI. You are talking to a coordinated team of specialists.

### The Boss: "Iris" (The Orchestrator)
Iris is the main point of contact. When you ask a question, Iris:
1.  Figures out exactly what you are asking.
2.  Identifies which companies or portfolios you are talking about.
3.  Delegates the actual research to the right "Specialist" on her team.
4.  Takes the specialist's report and presents it to you clearly.

Iris also has a **Memory**. She remembers your past questions, what kind of investor you are (e.g., beginner vs. advanced), and which stocks are on your watchlist.

### The Specialists (Sub-agents)
Iris manages a team of 7 specialized AI workers, each with a specific job:
1.  **Company Analyst:** Does a deep dive into a single company—checking its financials, health ratios (like P/E or Debt), recent news, and flagging risks.
2.  **Comparison Analyst:** Puts 2 to 5 companies side-by-side to tell you which one has better growth, margins, or valuation.
3.  **Portfolio Manager:** Looks at your current investments to tell you if you are taking on too much risk, if you are too exposed to one sector, and what news is affecting your holdings.
4.  **News Analyst:** Summarizes the latest headlines for a stock and tells you if the overall market sentiment is positive or negative.
5.  **Document Reader:** If you upload a specific PDF, this agent reads it and answers your questions, always citing the exact page number where it found the answer.
6.  **Theme Explorer:** If you want to invest in a broad idea like "Renewable Energy" or "AI," this agent searches all company filings to find businesses exposed to that theme.
7.  **Causal Detective:** (See below).

---

## 3. The Hidden Pattern Finder (Causal Intelligence)

This is the most advanced part of the platform. The **Causal Detective** agent is responsible for connecting global dots that aren't obvious on the surface.

It looks for "Domino Effects" (Causal Chains) in the real world to predict how stocks will move. 

**How a Causal Chain Works:**
1.  **The Trigger:** A geopolitical event happens (e.g., a conflict in the Middle East).
2.  **The Commodity:** This event causes a spike in a raw material price (e.g., crude oil prices go up).
3.  **The Sector:** The system knows which sectors depend on that material. For oil, it knows the Aviation sector uses it for jet fuel.
4.  **The Company Impact:** Higher fuel costs mean lower profit margins. Therefore, airline stocks might suffer in the coming weeks.

**Why this matters:**
Often, when a global event happens, the stock market doesn't react instantly to all the downstream effects. The Causal Intelligence engine monitors 11 of these specific chains and tracks how 19 different sectors are exposed to things like currency changes, metal prices, and energy costs. 

When you ask the AI, "Are there any hidden risks in my portfolio?" or "What's not obvious right now?", the Causal Detective uses this engine to warn you about these approaching domino effects before they hit a company's bottom line.

---

## Summary
In simple terms: The **ETL System** is the eyes and ears, constantly gathering and organizing data. The **Agent Architecture** is the brain, using specialized workers to analyze that data. And the **Causal Intelligence** engine is the intuition, predicting how global events will ripple through to your investments.
# MINERVA — Project Demo Video Script

**Project:** Minerva — AI-Native Equity Research Platform
**Team:** Ashutosh Kumar (1MS22CS036) · Sanchit Vijay (1MS22CS122) · Shamanth M. Hiremath (1MS22CS128)
**Guide:** Dr. Chandrika Prasad, Department of Computer Science and Engineering, M.S. Ramaiah Institute of Technology
**Estimated length:** 7–8 minutes
**Format:** Voice-over + on-screen demo (web app + diagram cuts)

> Reading guide — **[CAM]** = camera/face shot, **[SCREEN]** = product screen capture,
> **[DIAGRAM]** = architecture / flow diagram cut, **[B-ROLL]** = supporting visuals.
> Tonal direction is in *italics*; spoken voice-over is in plain text.

---

## 0 :00 — :15  | Cold Open / Hook

**[B-ROLL: stock-market tickers, a stack of 300-page annual reports, a confused-looking retail investor scrolling on a phone]**

*Calm, slightly serious.*

> In India today, more than seventy-five percent of adults are not financially literate.
> Less than one in twenty Indian households invest in equities — and most of those who do, do it without reading a single annual report.
> The information is out there. It's just locked inside thousands of pages of unstructured PDFs that nobody has time to read.

**[Cut to title card]**

> *We* built **Minerva** to fix that.

---

## 0 :15 — :45  | Problem Statement

**[CAM: presenter]**
**[SCREEN: a noisy NSE filings page, a 300-page PDF flipping past]**

> Modern equity research has a structural problem. Roughly *eighty percent* of every company's important financial intelligence — the risks, the management commentary, the footnotes, the forward-looking statements — lives entirely inside unstructured text.
>
> Traditional stock screeners are blind to that text. They can fetch a P/E ratio, but they cannot tell you that the auditor flagged a related-party transaction on page 247.
>
> And the obvious modern alternative — just asking ChatGPT — fails too. General-purpose language models *hallucinate* financial numbers, they get *lost in the middle* of long reports, and they cannot show you *where* their answer came from.
>
> For a retail investor in India, that combination is dangerous. We set out to build something better.

---

## 0 :45 — 1 :15  | Introducing Minerva

**[SCREEN: Minerva homepage / dashboard hero shot]**

> This is **Minerva**.
>
> Minerva is an *AI-native autonomous equity-research platform*. It ingests live regulatory filings from the NSE, the BSE, Financial Modelling Prep, and Alpha Vantage, and turns those filings into citation-grounded, decision-ready intelligence.
>
> Every answer Minerva gives is *attributed* — every number is traceable back to a bounding box on the source PDF, so the user can verify it themselves.
>
> Internally we call it an AI operating system for equity research. Externally, it gives a retail investor the kind of research workbench that, until now, only Bloomberg-terminal customers could afford.

---

## 1 :15 — 1 :45  | Objectives

**[DIAGRAM: bulleted overlay — six objectives, fade in one at a time]**

> When *we* scoped this project, we set six concrete engineering objectives:
>
> 1. Build a high-fidelity *Semantic ETL pipeline* that ingests NSE, BSE, FMP and Alpha Vantage filings.
> 2. Implement a *citation-grounded RAG pipeline* that guarantees a zero-hallucination contract.
> 3. Orchestrate a *multi-agent control plane* — not one giant prompt, but specialist sub-agents that collaborate.
> 4. Build an *embedding-based thematic discovery engine* that goes beyond rigid GICS sector codes.
> 5. Deliver an *integrated quantitative analytics dashboard* — HHI, CAPM, Sharpe, beta — for retail users.
> 6. And finally, *benchmark* the whole thing end-to-end against manual analyst workflows and unconstrained LLM wrappers.

---

## 1 :45 — 2 :45  | System Architecture

**[DIAGRAM: Five-layer architecture diagram — Client → Orchestration → Data Processing → Knowledge Base → Storage]**

> Minerva is a *layered microservices architecture*. There are five layers, each with one job.
>
> The **Client Layer** is a React 19 single-page application styled with Tailwind v4 and visualised with Recharts. That's where the chat, the dashboards and the document reader live.
>
> The **Orchestration Layer** is the brain. It runs on Python, FastAPI and LangGraph. This is where the *Router Agent* sits, and where every user query becomes a state machine.
>
> Underneath that is the **Data Processing Layer** — our Semantic ETL pipeline. This is where raw PDFs become clean, hashable, embeddable chunks.
>
> Then the **Knowledge Base Layer** — a Qdrant vector database with HNSW indexing for sub-millisecond similarity search, alongside the structured fundamentals.
>
> And finally the **Storage Layer** — a polyglot stack: PostgreSQL for relational metadata, AWS S3 for raw documents, and Redis as both a hot cache and a background-job broker.
>
> Everything is asynchronous, end-to-end. *We* deliberately picked async I/O so that LLM streams, vector lookups and database queries can overlap on the same event loop without ever blocking the request thread.

---

## 2 :45 — 3 :15  | ETL Pipeline & Data Sources

**[DIAGRAM: Pipeline animation — crawl → OCR → clean → chunk → embed → index]**

> Let's zoom in on the data plane, because Minerva is only as good as the data it reads.
>
> *We* ingest from four primary sources.
> From the **NSE** and the **BSE**, we crawl annual reports, quarterly results, board-meeting outcomes and corporate announcements — that's our unstructured PDF firehose.
> From **Financial Modelling Prep**, we pull clean structured fundamentals — income statements, balance sheets, cash-flow statements, ROE, ROCE, P/E ratios.
> From **Alpha Vantage**, we pull intraday and end-of-day OHLCV price series, plus commodity and FX time-series that feed our causal-intelligence module.
>
> Every document gets tagged with a (ticker, filing-date, document-type, source) tuple and every chunk gets an MD5 hash, so re-ingesting the same filing twice can never create duplicate vectors in Qdrant. That guarantees citation links stay unique and auditable.
>
> Chunking is *semantic*, not arbitrary. We split on structural headers — "Risk Factors", "Management Discussion" — into 512-word windows with 50-word overlap, so context never falls off the edge of a chunk.

---

## 3 :15 — 4 :00  | RAG, Embeddings & Citation Grounding

**[SCREEN: live Iris chat — user asks a question, Minerva streams an answer with click-through citation chips]**

> Once chunked, every piece of text becomes a high-dimensional vector. Minerva uses sentence-transformer embeddings — text-embedding-3-small in our production setup, with BGE and E5 as fallbacks.
>
> At query time the retriever computes *cosine similarity* between the user's question vector and every chunk vector in Qdrant, and pulls the top eight.
>
> But the most important rule in Minerva is what we call the **zero-hallucination contract**: *every* numerical claim in the answer must resolve to a bounding-box coordinate inside a source PDF, or to a row in PostgreSQL. If it can't, the answer is dropped before it ever reaches the user.
>
> That is what those small citation chips you see in the chat are. *We* don't ask the user to trust us — we let them verify every number with one click.

---

## 4 :00 — 5 :00  | Multi-Agent Orchestration & Deep Agents

**[DIAGRAM: LangGraph state machine — Router → DocInsight / Comparison / Forensic / Synthesis]**

> Now the part *we're* most proud of: the orchestration layer.
>
> Minerva does *not* run on a single giant prompt. It runs on a LangGraph state machine of specialist *deep agents*, and we built that for a very deliberate reason.
>
> When a user asks something like *"Compare HDFC Bank and ICICI Bank on asset quality and flag any forensic red flags from the last two annual reports"*, that's not one task — that's *five* tasks.
>
> So Minerva's **Router Agent** classifies the intent. If it's a simple ratio, it goes deterministically to PostgreSQL via the FMP toolset. If it's a qualitative read of a filing, it goes to the **Doc-Insight Agent** with vector retrieval. If it's a peer comparison, it goes to the **Comparison Agent**, which spawns two parallel Company Agents. If it's an accounting-quality scan, the **Forensic Agent** takes over with its own toolset.
>
> Whatever each sub-agent returns flows into the **Synthesis Agent**, which enforces the citation contract and streams the final answer back through a WebSocket.
>
> *Why deep agents?* Because a deep agent isn't just a router — it carries its own planning loop, its own memory, and its own tool firewall. When the Forensic Agent runs, it literally *cannot* call the comparison tool by mistake — the action space is masked. That's how Minerva gets to ninety-four-percent agent convergence on a thousand-query stress test without going off the rails.
>
> A single monolithic agent collapses on this kind of compound query. A team of specialised deep agents *thrives* on it.

---

## 5 :00 — 5 :45  | Choice of Models, APIs & Provider Factory

**[DIAGRAM: provider-factory icon — OpenAI / Groq / DeepSeek / Ollama feeding into the orchestrator]**

> One more architectural decision worth calling out — Minerva is *provider-agnostic*.
>
> We built a small factory pattern around the LLM and the embedding layer. At runtime, Minerva can talk to OpenAI for deep reasoning, Groq for ultra-fast LPU inference on the latency-critical path, DeepSeek for cost-sensitive bulk operations, or Ollama for fully air-gapped, on-device inference.
>
> The same LangGraph graph runs unchanged on all four. *We* chose this because in real production — and especially in an Indian regulatory context where data residency matters — locking yourself to one vendor is a liability, not a feature.
>
> The same factory pattern wraps the embeddings, so we can swap text-embedding-3-small for BGE or E5 with one environment variable.

---

## 5 :45 — 6 :30  | Results & Performance

**[SCREEN: results dashboard with the comparison table from the report]**

> Let's talk about whether it actually works.
>
> *We* benchmarked Minerva end-to-end on a thousand-query stress test against two baselines — a traditional keyword screener, and a generic LLM wrapper.
>
> On **research latency**, Minerva resolves the average query in about two-and-a-half seconds. A human analyst on the same query takes around three hundred seconds. That's a *ninety-nine percent reduction*.
>
> On **retrieval accuracy**, Minerva scores 92.5% against the keyword screener's 68%.
>
> On **thematic precision** — finding the right companies for an emerging theme like "AI infrastructure" — Minerva hits 85% against the screener's 35%.
>
> On **forensic recall** — surfacing the kind of accounting red flag that a manual scan would miss — Minerva is at 88% versus 42%.
>
> And critically, across the entire benchmark, our zero-hallucination contract held in *one hundred percent* of evaluated answers. Every number resolved to a source.
>
> Peak memory under a sixty-minute stress load stayed at fourteen-point-five gigabytes — comfortably under our sixteen-gigabyte commercial cloud-server budget.

---

## 6 :30 — 7 :00  | Live Demo Beats

**[SCREEN: 3 fast cuts of the actual product]**

> Here's Minerva in action.
>
> *Cut 1 — Thematic Discovery.* I ask, "Which Indian companies have meaningful exposure to AI infrastructure?" — and the embedding-based engine surfaces names that aren't classified under "IT Services" by any traditional sector code.
>
> *Cut 2 — Iris Chat.* I ask, "Summarise the auditor's qualifications in the latest annual report for this ticker," and Minerva streams the answer back with three clickable citations, each opening the exact paragraph in the PDF.
>
> *Cut 3 — Portfolio Dashboard.* I upload a portfolio, and Minerva computes its Herfindahl–Hirschman concentration score, its CAPM expected return, its Sharpe ratio, and flags a commodity-shock alert from the Causal Geo-Intelligence module.

---

## 7 :00 — 7 :45  | The Why — Financial Literacy in India

**[B-ROLL: classroom shots, a parent and child looking at a phone, the Indian map with statistics overlay]**

*Slightly slower, warmer.*

> Now — *why does any of this matter?*
>
> According to the S&P Global FinLit Survey, India's adult financial-literacy rate is about *twenty-four percent*. That places us seventy-first in the world. The National Centre for Financial Education puts the number closer to *twenty-seven percent*, and for Indian women, the figure drops to around *twenty-one percent*.
>
> Today there are more than fifteen crore demat accounts in India. But fewer than three percent of household wealth is held in equities — the vast majority sits in real estate and gold, mostly because Indian families don't trust what they don't understand.
>
> And the next generation isn't catching up on its own. Financial literacy isn't part of most school curricula. Most Indian kids grow up not knowing what a balance sheet is, let alone how to read an annual report.
>
> Minerva is *our* answer to that gap. By turning a three-hundred-page filing into a plain-English, citation-backed two-line summary, we make institutional-grade equity research accessible to a college student in Tier-3 India, to a small-business owner in Bengaluru, and to a curious fifteen-year-old learning what a stock actually *is*.
>
> *We* believe financial awareness is the next public-good problem AI should solve in India. And Minerva is *our* contribution to that mission.

---

## 7 :45 — 8 :00  | Close

**[CAM: full team on screen]**

> *We* are Ashutosh Kumar, Sanchit Vijay, and Shamanth M. Hiremath, from the Department of Computer Science and Engineering at M.S. Ramaiah Institute of Technology, under the guidance of Dr. Chandrika Prasad.
>
> This is **Minerva** — autonomous, citation-grounded, multi-agent equity research, built for India.
>
> Thank you for watching.

**[End card: Minerva logo + team names + project URL / QR code]**

---

# APPENDIX

## A. One-paragraph teaser version (for the YouTube description)

> Minerva is an AI-native equity-research platform that ingests live filings from NSE, BSE, FMP and Alpha Vantage, semantic-chunks them into a Qdrant vector index, and answers natural-language questions through a LangGraph multi-agent orchestrator. Every numerical claim is citation-grounded to its source PDF, every sub-agent is action-masked, and every answer streams back in roughly 2.5 seconds — a 99% reduction over manual analyst workflows. Our mission: democratise institutional-grade equity research for the 76% of Indian adults who currently lack basic financial literacy.

## B. Suggested on-screen statistics (verify before use)

| Stat                                                       | Source                                          |
|------------------------------------------------------------|-------------------------------------------------|
| 24% adult financial literacy in India (rank 71/144)        | S&P Global FinLit Survey                        |
| ≈27% per India-specific surveys                            | National Centre for Financial Education (NCFE)  |
| ~21% financial literacy among Indian women                 | NCFE / RBI publications                         |
| 15+ crore demat accounts in India (2024)                   | NSDL / CDSL public data                         |
| <5% of household savings in equities                       | RBI Handbook of Statistics                      |
| ~50% of household wealth in real estate, ~11% in gold      | RBI Household Finance Committee Report          |

> **Note for the team:** the exact numbers above shift each year — pull the latest figures from SEBI, RBI and NCFE the week of the recording so the slides match the most current data.

## C. Suggested B-roll shopping list

- Stack of physical annual reports being flipped (slow-motion).
- Over-the-shoulder shot of a phone scrolling NSE corporate-filings.
- Tight macro shot of Recharts visualisations animating.
- Classroom / college students working on laptops.
- Indian map with literacy overlay (animated infographic).
- Quick montage of Minerva UI: dashboard → chat → comparison view → forensic alert.

## D. Talking-point cheat sheet (for QA after the demo)

- *Why LangGraph and not a single agent?* — Compound queries need specialist routing; action masking prevents tool-misuse.
- *Why Qdrant?* — HNSW indexing, sub-millisecond cosine search, easy self-host.
- *Why this provider factory?* — Vendor neutrality, data-residency optionality (Ollama for air-gapped), cost control.
- *How do you guarantee zero-hallucination?* — Hard contract in the Synthesis Agent: drop any claim missing a source pointer.
- *How does it stay under 16 GB RAM?* — Streaming responses, K-path caching, semantic chunking instead of full-document context loading.
- *Why does it matter for India?* — 76% adults are not financially literate; Minerva makes institutional-grade research accessible.
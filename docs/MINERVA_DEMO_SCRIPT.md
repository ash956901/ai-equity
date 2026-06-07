# MINERVA — Project Demo Video Script

**Project:** Minerva — AI-Native Equity Research Platform
**Team:** Ashutosh Kumar (1MS22CS036) · Sanchit Vijay (1MS22CS122) · Shamanth M. Hiremath (1MS22CS128)
**Guide:** Dr. Chandrika Prasad, Department of Computer Science and Engineering, M.S. Ramaiah Institute of Technology
**Runtime:** ~4 min 30 sec spoken · ~800 words

---

## The Quiet Problem

Picture a curious young Indian who wants to invest in a company. She opens its annual report. It is three hundred pages long. Inside it sit the risks, the footnotes, the auditor's quiet admissions — eighty percent of everything that actually matters. She scrolls for ten minutes and gives up.

This is the problem *we* set out to solve. The most important financial information in the world is public, but it is locked inside walls of dense, unstructured text. Traditional stock screeners only see numbers — they cannot tell you that the auditor flagged a related-party transaction on page two hundred forty-seven. And general-purpose AI like ChatGPT sounds confident but hallucinates and never shows its sources. For a retail investor risking real money, *"trust me"* is not good enough.

There are four pain points *we* keep coming back to. First — **information overload**: too many filings, too few hours. Second — **hidden risk**: the danger sits in the *text* the numbers cannot see. Third — **hallucination**: today's AI invents numbers and will not show its sources. And fourth — **domino blindness**: a war or a policy change in one corner of the world quietly rewrites the math for a stock in your portfolio, and nobody warns you.

## Meet Minerva

So *we* built **Minerva** — an AI research analyst that never sleeps, reads every filing published by companies, and answers any question about an Indian company in seconds, with every claim backed by a clickable citation. Think of Minerva as the research desk of a global investment bank — the kind that, until now, only Bloomberg-terminal subscribers could afford — miniaturised and built for India.

## What We Set Out To Do

We started with six clear goals. Ingest every NSE and BSE filing live and turn it into searchable knowledge. Never hallucinate — every number must be traceable to a real source. Replace one big general-purpose AI with a *team* of specialist AIs. Find investment themes traditional screeners miss. Give the everyday investor the same risk math hedge funds use. And finally, surface the *hidden* ripple effects — like how a conflict in the Middle East quietly squeezes an Indian airline's margins.

Each pain point became a design pillar. Overload — *we* built a **Semantic ETL pipeline** that reads every filing for you. Hidden risk — *we* built specialist agents that read the *text*, not just the numbers. Hallucination — every Minerva answer is **citation-grounded**; if a claim cannot be sourced, it is dropped. Domino blindness — *we* built a **Causal Detective** that watches the chains nobody else watches.

## How Minerva Sees the World

Minerva is built in three layers — the **Eyes and Ears** that watch the market twenty-four hours a day, the **Brain** that reasons, and the **Voice** which is our React app where the user talks to Minerva.

The data heartbeat runs around the clock. Every morning at six AM India time, Minerva re-syncs the entire NSE and BSE universe. Every six hours, fresh news from NewsAPI and NewsData.io is run through a FinBERT sentiment classifier. Twice a day, fresh PDFs are broken into semantic chunks and stored as searchable vectors in **Qdrant**. In the background, Minerva tracks commodity prices from Alpha Vantage and geopolitical events from GDELT — the same feed intelligence analysts use. Live broker quotes come from **Upstox** and **Kite by Zerodha** — the brokers Indian retail actually uses. Global fundamentals from FMP and macro signals from FRED round it out.

## The Brain — IRIS and the Eight Specialists

When you walk into a real research firm, you do not meet one person who knows everything. You meet a *team* who collaborate. Minerva works the same way.

At the top sits **IRIS** — our orchestrator, the chief analyst. When a question arrives, IRIS reads it, decides which specialists are needed, and dispatches the work. Beneath her are eight specialists: the **Company Analyst**, the **Comparison Analyst**, the **Portfolio Manager**, the **News Analyst**, the **Document Reader**, the **Thematic Explorer**, the **Causal Detective** — who traces hidden domino chains across sectors — and the **Performance Analyst**. They share a common toolbox of eleven tools.

A few of those causal chains tell the story best. When the Government of India raises the ethanol-blending mandate in petrol, sugar mills quietly benefit, because ethanol is a sugarcane by-product — a policy aimed at energy becomes a tailwind for the sugar industry. When AI data centers boom, the real winners are not just AI companies — they are the chip foundries, the industrial-lubricant makers, the liquid-coolant suppliers, the spare-parts vendors, the power-equipment manufacturers, and even the data-center real-estate plays. And when conflict flares in the Middle East, the ripple does not stop at crude oil — it hits Indian airlines through jet-fuel costs, and Indian auto manufacturers through input-cost squeeze and supply-chain shocks. Minerva sees these chains so the user does not have to.

## Why Deep Agents — Why This Wins

A single general-purpose AI is like asking one person to be a doctor, a lawyer, and an accountant all at once. It works for small questions and collapses on big ones.

A *deep agent* is different. Each one carries its own memory, its own plan, and its own restricted toolbox. When the Causal Detective is reasoning, it cannot reach into the Portfolio Manager's toolkit by mistake. We wire them together using **LangGraph** as a state machine, so Minerva reasons in multiple steps — retrieve, calculate, cross-reference, synthesise — instead of guessing in a single shot. The research paper measured the payoff: ninety-four percent routing accuracy, a 4.2-out-of-5 expert rating, sub-ten-second responses. And the same Minerva runs swappably on Claude, Groq, OpenAI, DeepSeek, or a fully local Ollama — never locked to one vendor.

## Let's Walk Through Minerva

Let's walk through our Minerva system — starting from the top of the navigation.

**Dashboard.** The first screen after login. It shows the market at a glance: live NSE and BSE company cards, a sector heatmap, a portfolio summary widget, and the day's active alerts. It is the control room — a user knows within five seconds whether anything needs attention today. Every widget refreshes from the data the ETL pipeline brought in overnight.

**Compare.** Side-by-side deep comparison of two or more companies. The user picks tickers; Minerva pulls financials, ratios, filing sentiment, and management quality signals and lays them in parallel columns. The Comparison Analyst sub-agent synthesises a written verdict — not just numbers side by side, but a reasoned, cited judgment on which company looks stronger and why.

**Company Workspace.** The full research dossier for a single company. Live stock price, income statement, balance sheet, cash-flow statement, key ratios, an LLM-generated business summary, flagged risks from the last filing, and a document viewer — all on one screen. The Company Analyst agent is on call for any follow-up question about that company.

**Minerva Chat.** The heart of the platform. The user types any natural-language question — "What were Reliance's capital expenditure trends over the last three years?" or "Which Indian cement companies have the best cost efficiency?" — and IRIS assembles the right specialists, retrieves the relevant filing passages, computes the needed numbers, and streams a cited answer back in seconds. Every number carries a source chip. Click it, and the source document opens at the exact passage.

**Discovery.** Thematic investment discovery. Instead of navigating rigid sector codes, the user types a theme — "rural consumption", "data-centre real estate", "electric vehicle supply chain" — and Minerva runs a semantic search across all indexed filings and news, surfacing companies that match the theme even when those companies never use those exact words in their own disclosures.

**Portfolio.** The user's holdings, fully analysed. Portfolio beta, Sharpe ratio, HHI concentration score, sector-exposure donut chart, and a live causal-alert panel that flags when a geopolitical or commodity event touches something the user actually owns. The Portfolio Manager agent recalculates in the background whenever the market moves.

**Domino Effect.** Our signature causal intelligence view. The user picks a trigger — "India raises ethanol-blending mandate" or "Middle East conflict escalates" — and Minerva maps the full chain: from the event, through the commodity it moves, through every sector it touches, to the specific listed companies that benefit or suffer. Each node is clickable and sourced. This is the view that surfaces risks traditional screeners are entirely blind to.

**Money.** A financial deep-dive: full income statements, balance sheets, and cash-flow statements with multi-year comparison charts, for users who want the raw numbers without an AI layer in between.

**Performance.** Attribution and backtesting. How has a portfolio performed against a benchmark? Which holdings contributed and which dragged? Broken down by period and sector.

**Simulator.** The paper-trading sandbox — the user practises on live prices without risking a single rupee. Covered in more depth next.

**Filings.** Document library. Every NSE and BSE filing Minerva has ingested, browsable by company and date, full-text searchable. Click any document to open the embedded PDF viewer.

**Timeline.** A chronological feed of filings, earnings announcements, news headlines, and price events for the companies the user follows — all in one scrollable river, newest first.

**News.** Market headlines filtered and FinBERT sentiment-scored. Each article shows a bullish, bearish, or neutral tag and an impact-score indicator. Filter by sector, company, or keyword.

**Profile.** User identity, portfolio preferences, and broker-connection settings. Supports multiple named profiles — a parent and a college student can share one account with separate portfolios.

**Settings.** LLM provider preference, notification thresholds, and data-refresh intervals.

## Learn Before You Earn — The Gamified Simulator

Knowing the market is one thing. *Trusting yourself* with real money is another. Most Indians who avoid the stock market are not lazy — they are afraid of losing money they cannot afford to lose. So *we* built the **Minerva Simulator**: a paper-trading sandbox where users can practise on live Indian market data without risking a single rupee.

And *we* gamified it. Every simulated trade earns **XP**. Building a diversified portfolio unlocks **badges**. Logging in to review the market every day builds a **streak**. A first-time investor — or a fifteen-year-old learning what a stock actually *is* — can spend a month placing fake trades, getting feedback from the same eight Minerva agents that institutional users get, and graduating to real money only when they feel ready. *We* think of it as a flight simulator for the stock market: you crash here so you do not crash out there.

## Why This Matters — Financial Literacy in India

Now — *why does any of this matter?*

According to the S&P Global FinLit Survey, only **twenty-four percent** of Indian adults are financially literate. That places India **seventy-first in the world**. For Indian women, the number drops to **twenty-one percent**. India has crossed **fifteen crore demat accounts**, yet **less than five percent of household wealth** sits in equities. Most still goes into real estate and gold.

Indian families do not avoid the stock market because they lack money. They avoid it because they do not trust what they do not understand. And nobody is teaching them. Financial literacy is not in the school syllabus. Most Indian kids grow up not knowing what a balance sheet is, let alone how to read one.

Minerva is *our* answer to that gap. It turns a three-hundred-page filing into a plain-English summary a fifteen-year-old can follow, with citations they can click and verify. It gives a college student in Tier-3 India, a small-business owner in Bengaluru, and a curious teenager in Hyderabad the same workbench a Goldman Sachs analyst uses in New York. *We* believe financial awareness is the next public-good problem AI should solve in India — and Minerva is *our* contribution.

## Close

*We* are Ashutosh, Sanchit, and Shamanth — from the Department of Computer Science and Engineering at MSRIT, under the guidance of Dr. Chandrika Prasad. This has been **Minerva** — autonomous, citation-grounded, and built for India. Thank you for watching.

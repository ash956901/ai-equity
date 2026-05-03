# Database Schema Design – AI Equity Research Platform

> **Status (as of Round 2):** historical design document. The shipped schema overlaps but has additions (asymmetric flags on `company_themes`, `filing_summaries`, `chart_series`, `statement_items`, `transactions`, `alert_events`, `system_config`, etc.) and the User table has Round 2 auth columns. **For the actual table list and migration order, see [SHIPPED.md](./SHIPPED.md) and `backend-ai/alembic/versions/`.** Original design retained as reference.

## Overview

This document defines the **PostgreSQL schema** for the AI-native equity research platform, optimized for Indian equities with support for large-scale financial data, document metadata, portfolio management, and chat-based interactions.

---

## Design Principles

1. **Normalized financial data** – Store raw statements in normalized form; compute ratios on-demand or cache them.
2. **India-first** – NSE/BSE ticker support, ISIN, Indian sector/industry classifications, INR as default currency.
3. **Cloud-friendly** – Use UUIDs for primary keys; store large blobs (PDFs, images) in object storage (S3/Blob), only URIs in DB.
4. **Audit trails** – All tables include `created_at`, `updated_at`; critical tables include `created_by`, `updated_by`.
5. **Idempotency** – Use unique constraints and hashes to prevent duplicate ingestion.
6. **Performance** – Index on common query patterns: `(company_id, period)`, `(company_id, filing_date)`, `(user_id, created_at)`.

---

## Core Tables

### 1. Companies & Securities

#### `companies`

Master table for all listed and tracked companies.

```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(500),
    ticker_nse VARCHAR(20),
    ticker_bse VARCHAR(20),
    isin VARCHAR(12) UNIQUE,
    cin VARCHAR(21),  -- Corporate Identification Number (India)
    sector VARCHAR(100),
    industry VARCHAR(100),
    sub_industry VARCHAR(100),
    country VARCHAR(3) DEFAULT 'IND',
    website_domain VARCHAR(255),
    ir_page_url TEXT,  -- Investor Relations URL
    description TEXT,
    market_cap_inr BIGINT,
    listing_status VARCHAR(20) DEFAULT 'active',  -- active, delisted, suspended
    listing_date DATE,
    delisting_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_companies_ticker_nse ON companies(ticker_nse);
CREATE INDEX idx_companies_ticker_bse ON companies(ticker_bse);
CREATE INDEX idx_companies_isin ON companies(isin);
CREATE INDEX idx_companies_sector ON companies(sector);
```

#### `exchanges`

Reference table for stock exchanges.

```sql
CREATE TABLE exchanges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(10) UNIQUE NOT NULL,  -- NSE, BSE
    name VARCHAR(100) NOT NULL,
    country VARCHAR(3) DEFAULT 'IND',
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `securities`

Maps company securities to exchanges and indices.

```sql
CREATE TABLE securities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    exchange_id UUID NOT NULL REFERENCES exchanges(id),
    symbol VARCHAR(50) NOT NULL,
    isin VARCHAR(12),
    series VARCHAR(10),  -- EQ, BE, etc. (NSE series)
    face_value DECIMAL(10,2),
    lot_size INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(exchange_id, symbol)
);

CREATE INDEX idx_securities_company ON securities(company_id);
CREATE INDEX idx_securities_symbol ON securities(symbol);
```

#### `indices`

Stock market indices (Nifty 50, Nifty 500, sectoral indices).

```sql
CREATE TABLE indices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,  -- NIFTY50, NIFTY500, BANKNIFTY
    name VARCHAR(100) NOT NULL,
    exchange_id UUID REFERENCES exchanges(id),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `index_constituents`

Maps companies to indices.

```sql
CREATE TABLE index_constituents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    index_id UUID NOT NULL REFERENCES indices(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    weight DECIMAL(5,4),  -- Percentage weight in index
    added_date DATE,
    removed_date DATE,
    is_current BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(index_id, company_id, added_date)
);

CREATE INDEX idx_index_constituents_index ON index_constituents(index_id);
CREATE INDEX idx_index_constituents_company ON index_constituents(company_id);
```

---

### 2. Financial Data

#### `financial_statements_raw`

Normalized storage for all financial statement line items.

```sql
CREATE TABLE financial_statements_raw (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    source_filing_id UUID REFERENCES filings(id),  -- Link to source document
    statement_type VARCHAR(50) NOT NULL,  -- P&L, Balance_Sheet, Cash_Flow, Ratios, Segment
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    fiscal_year INT NOT NULL,
    quarter INT,  -- 1, 2, 3, 4 or NULL for annual
    is_audited BOOLEAN DEFAULT FALSE,
    is_consolidated BOOLEAN DEFAULT TRUE,
    line_item VARCHAR(255) NOT NULL,  -- Standardized line item name
    value DECIMAL(20,2),
    currency VARCHAR(3) DEFAULT 'INR',
    unit VARCHAR(20) DEFAULT 'Cr',  -- Cr, Lakh, Million, etc.
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_fin_raw_company_period ON financial_statements_raw(company_id, period_end DESC);
CREATE INDEX idx_fin_raw_company_fy ON financial_statements_raw(company_id, fiscal_year, quarter);
CREATE INDEX idx_fin_raw_statement_type ON financial_statements_raw(statement_type);
CREATE UNIQUE INDEX idx_fin_raw_unique ON financial_statements_raw(
    company_id, statement_type, period_end, line_item, is_consolidated
);
```

#### `financial_ratios`

Precomputed financial ratios and metrics for fast querying.

```sql
CREATE TABLE financial_ratios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    period_end DATE NOT NULL,
    fiscal_year INT NOT NULL,
    quarter INT,
    
    -- Profitability
    roe DECIMAL(8,4),  -- Return on Equity
    roce DECIMAL(8,4),  -- Return on Capital Employed
    roa DECIMAL(8,4),  -- Return on Assets
    gross_margin DECIMAL(8,4),
    ebitda_margin DECIMAL(8,4),
    ebit_margin DECIMAL(8,4),
    net_margin DECIMAL(8,4),
    
    -- Leverage
    debt_to_equity DECIMAL(10,4),
    debt_to_assets DECIMAL(8,4),
    interest_coverage DECIMAL(10,4),
    
    -- Liquidity
    current_ratio DECIMAL(8,4),
    quick_ratio DECIMAL(8,4),
    cash_ratio DECIMAL(8,4),
    
    -- Efficiency
    asset_turnover DECIMAL(8,4),
    inventory_turnover DECIMAL(8,4),
    receivables_turnover DECIMAL(8,4),
    
    -- Valuation (if market data available)
    pe_ratio DECIMAL(10,4),
    pb_ratio DECIMAL(10,4),
    ev_ebitda DECIMAL(10,4),
    price_to_sales DECIMAL(10,4),
    
    -- Growth (YoY)
    revenue_growth_yoy DECIMAL(8,4),
    ebitda_growth_yoy DECIMAL(8,4),
    pat_growth_yoy DECIMAL(8,4),
    eps_growth_yoy DECIMAL(8,4),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, period_end, quarter)
);

CREATE INDEX idx_fin_ratios_company_period ON financial_ratios(company_id, period_end DESC);
```

#### `statement_items`

Generic table for ad-hoc financial disclosures (segmental data, geographic splits, etc.).

```sql
CREATE TABLE statement_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    source_filing_id UUID REFERENCES filings(id),
    period_end DATE NOT NULL,
    fiscal_year INT NOT NULL,
    quarter INT,
    context_heading VARCHAR(255),  -- e.g., "Revenue by Geography", "Segment Performance"
    row_label VARCHAR(255),
    column_label VARCHAR(255),
    value DECIMAL(20,2),
    unit VARCHAR(20) DEFAULT 'Cr',
    currency VARCHAR(3) DEFAULT 'INR',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_statement_items_company ON statement_items(company_id, period_end DESC);
```

---

### 3. Filings & Documents

#### `filings`

Metadata for all regulatory filings and investor documents.

```sql
CREATE TABLE filings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    exchange_id UUID REFERENCES exchanges(id),
    filing_type VARCHAR(100) NOT NULL,  -- Annual_Report, Quarterly_Results, Concall, Presentation, Press_Release, etc.
    title TEXT NOT NULL,
    filing_date DATE NOT NULL,
    period_start DATE,
    period_end DATE,
    source_url TEXT,
    raw_uri TEXT,  -- S3/Blob path to original PDF/PPTX
    parsed_text_uri TEXT,  -- S3/Blob path to extracted text JSON
    document_hash VARCHAR(64) UNIQUE,  -- SHA-256 for idempotency
    status VARCHAR(20) DEFAULT 'pending',  -- pending, parsed, embedded, failed
    error_message TEXT,
    metadata JSONB,  -- Flexible storage for extra fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_filings_company_date ON filings(company_id, filing_date DESC);
CREATE INDEX idx_filings_type ON filings(filing_type);
CREATE INDEX idx_filings_status ON filings(status);
CREATE UNIQUE INDEX idx_filings_unique ON filings(company_id, filing_type, filing_date, document_hash);
```

#### `filing_pages`

Page-level metadata for multi-page documents (optional, for fine-grained linking).

```sql
CREATE TABLE filing_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filing_id UUID NOT NULL REFERENCES filings(id) ON DELETE CASCADE,
    page_number INT NOT NULL,
    text_content TEXT,
    has_tables BOOLEAN DEFAULT FALSE,
    has_charts BOOLEAN DEFAULT FALSE,
    vector_chunk_ids TEXT[],  -- Array of vector DB chunk IDs for this page
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(filing_id, page_number)
);

CREATE INDEX idx_filing_pages_filing ON filing_pages(filing_id);
```

#### `chart_series`

Structured data extracted from charts/diagrams in filings.

```sql
CREATE TABLE chart_series (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    source_filing_id UUID REFERENCES filings(id),
    chart_image_uri TEXT,  -- S3/Blob path to chart image
    metric_name VARCHAR(255),  -- e.g., "Revenue by Region", "EBITDA Margin Trend"
    category VARCHAR(100),  -- e.g., "Geography", "Product", "Time"
    period DATE,
    label VARCHAR(255),  -- x-axis label or category name
    value DECIMAL(20,2),
    unit VARCHAR(20),
    currency VARCHAR(3) DEFAULT 'INR',
    extraction_confidence DECIMAL(4,3),  -- 0.0 to 1.0
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chart_series_company ON chart_series(company_id, period DESC);
CREATE INDEX idx_chart_series_metric ON chart_series(metric_name);
```

---

### 4. News & Sentiment

#### `news_articles`

News articles with sentiment analysis.

```sql
CREATE TABLE news_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,  -- Nullable for macro news
    headline TEXT NOT NULL,
    body TEXT,
    source VARCHAR(100),  -- GNews, NewsAPI, RSS, etc.
    source_url TEXT UNIQUE,
    published_at TIMESTAMP NOT NULL,
    fetched_at TIMESTAMP DEFAULT NOW(),
    
    -- Sentiment
    sentiment_score DECIMAL(5,4),  -- -1.0 to 1.0
    sentiment_label VARCHAR(20),  -- positive, negative, neutral
    impact_level VARCHAR(20),  -- High, Medium, Low
    relevance_confidence DECIMAL(4,3),  -- 0.0 to 1.0
    affected_dimension VARCHAR(50),  -- earnings, regulation, management, macro, etc.
    
    -- Metadata
    tickers TEXT[],  -- Array of mentioned tickers
    keywords TEXT[],
    language VARCHAR(10) DEFAULT 'en',
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_news_company_published ON news_articles(company_id, published_at DESC);
CREATE INDEX idx_news_published ON news_articles(published_at DESC);
CREATE INDEX idx_news_sentiment ON news_articles(sentiment_score);
```

---

### 5. Themes & Discovery

#### `company_themes`

Theme tagging for discovery (AI, defense, renewables, data centers, etc.).

```sql
CREATE TABLE company_themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    theme_name VARCHAR(100) NOT NULL,  -- AI, Blockchain, EV, Defense, Data_Centers, etc.
    exposure_type VARCHAR(50),  -- direct, indirect, supply_chain, customer
    confidence_score DECIMAL(4,3),  -- 0.0 to 1.0
    impact_score DECIMAL(4,3),  -- Expected revenue/profit impact (0.0 to 1.0)
    reasoning TEXT,  -- LLM-generated explanation
    detected_at TIMESTAMP DEFAULT NOW(),
    validated_by VARCHAR(50),  -- agent_name or manual
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, theme_name)
);

CREATE INDEX idx_company_themes_company ON company_themes(company_id);
CREATE INDEX idx_company_themes_theme ON company_themes(theme_name);
CREATE INDEX idx_company_themes_confidence ON company_themes(confidence_score DESC);
```

#### `company_web_endpoints`

Discovered investor relations endpoints per company.

```sql
CREATE TABLE company_web_endpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    base_domain VARCHAR(255) NOT NULL,
    endpoint_path TEXT NOT NULL,
    endpoint_type VARCHAR(50),  -- investor_relations, financials, press_releases, concalls
    is_validated BOOLEAN DEFAULT FALSE,
    last_crawled_at TIMESTAMP,
    crawl_frequency_days INT DEFAULT 7,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, endpoint_path)
);

CREATE INDEX idx_web_endpoints_company ON company_web_endpoints(company_id);
```

---

### 6. Portfolio Management

#### `users`

User accounts.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),  -- bcrypt or similar
    full_name VARCHAR(255),
    expertise_level VARCHAR(20) DEFAULT 'beginner',  -- beginner, intermediate, advanced
    risk_tolerance VARCHAR(20),  -- conservative, moderate, aggressive
    investment_horizon VARCHAR(20),  -- short, medium, long
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
```

#### `portfolios`

User portfolios (can have multiple per user).

```sql
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    broker VARCHAR(50),  -- zerodha, kotak, groww, manual
    broker_account_id VARCHAR(100),
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)
);

CREATE INDEX idx_portfolios_user ON portfolios(user_id);
```

#### `holdings`

Current holdings in a portfolio.

```sql
CREATE TABLE holdings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id),
    quantity DECIMAL(15,4) NOT NULL,
    average_price DECIMAL(15,4),
    current_price DECIMAL(15,4),
    currency VARCHAR(3) DEFAULT 'INR',
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(portfolio_id, company_id)
);

CREATE INDEX idx_holdings_portfolio ON holdings(portfolio_id);
CREATE INDEX idx_holdings_company ON holdings(company_id);
```

#### `transactions`

Transaction history.

```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id),
    transaction_type VARCHAR(20) NOT NULL,  -- buy, sell, dividend, bonus, split
    quantity DECIMAL(15,4) NOT NULL,
    price DECIMAL(15,4),
    amount DECIMAL(20,2),
    currency VARCHAR(3) DEFAULT 'INR',
    transaction_date DATE NOT NULL,
    broker_transaction_id VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transactions_portfolio ON transactions(portfolio_id, transaction_date DESC);
```

#### `portfolio_metrics`

Precomputed portfolio-level metrics.

```sql
CREATE TABLE portfolio_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    computed_at TIMESTAMP NOT NULL,
    
    -- Allocation
    total_value_inr DECIMAL(20,2),
    equity_allocation DECIMAL(5,4),
    cash_allocation DECIMAL(5,4),
    
    -- Concentration
    top_holding_pct DECIMAL(5,4),
    top_5_holdings_pct DECIMAL(5,4),
    herfindahl_index DECIMAL(8,6),  -- Concentration measure
    
    -- Sector exposure
    sector_allocation JSONB,  -- {sector: percentage}
    
    -- Risk
    portfolio_beta DECIMAL(8,4),  -- vs Nifty
    portfolio_volatility DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    
    -- Performance
    total_return_1m DECIMAL(8,4),
    total_return_3m DECIMAL(8,4),
    total_return_1y DECIMAL(8,4),
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_portfolio_metrics_portfolio ON portfolio_metrics(portfolio_id, computed_at DESC);
```

---

### 7. Chat & Memory

#### `chat_sessions`

User chat sessions.

```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    context_type VARCHAR(50),  -- general, company_analysis, portfolio, comparison
    context_ids JSONB,  -- Flexible storage for company_ids, portfolio_id, etc.
    is_active BOOLEAN DEFAULT TRUE,
    last_message_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chat_sessions_user ON chat_sessions(user_id, created_at DESC);
```

#### `chat_messages`

Individual messages in a chat session.

```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- user, assistant, system
    content TEXT NOT NULL,
    metadata JSONB,  -- Tool calls, sources, etc.
    tokens_used INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_session ON chat_messages(session_id, created_at);
```

#### `user_uploads`

User-uploaded documents for analysis.

```sql
CREATE TABLE user_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50),  -- pdf, pptx, xlsx, etc.
    file_size_bytes BIGINT,
    raw_uri TEXT NOT NULL,  -- S3/Blob path
    parsed_text_uri TEXT,
    document_hash VARCHAR(64),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, parsed, embedded, failed
    vector_namespace VARCHAR(100),  -- User-specific namespace in vector DB
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_uploads_user ON user_uploads(user_id, created_at DESC);
CREATE INDEX idx_user_uploads_session ON user_uploads(session_id);
```

---

### 8. ETL & System

#### `etl_runs`

Log of all ETL pipeline executions.

```sql
CREATE TABLE etl_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_name VARCHAR(100) NOT NULL,  -- nse_filings, investor_crawler, news_ingestion, etc.
    run_type VARCHAR(20) DEFAULT 'scheduled',  -- scheduled, manual, on_demand
    company_id UUID REFERENCES companies(id),  -- NULL for full runs
    status VARCHAR(20) NOT NULL,  -- running, completed, failed, partial
    records_processed INT DEFAULT 0,
    records_failed INT DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_etl_runs_pipeline ON etl_runs(pipeline_name, started_at DESC);
CREATE INDEX idx_etl_runs_status ON etl_runs(status);
```

#### `system_config`

System-wide configuration key-value store.

```sql
CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Indexes Summary

Key indexes for performance:

- **Companies**: `ticker_nse`, `ticker_bse`, `isin`, `sector`
- **Financial statements**: `(company_id, period_end)`, `(company_id, fiscal_year, quarter)`
- **Filings**: `(company_id, filing_date)`, `filing_type`, `status`
- **News**: `(company_id, published_at)`, `published_at`, `sentiment_score`
- **Portfolios**: `(user_id)`, `(portfolio_id, company_id)`
- **Chat**: `(user_id, created_at)`, `(session_id, created_at)`

---

## Migration Strategy

1. Start with core tables: `companies`, `exchanges`, `securities`, `indices`.
2. Add financial data tables: `financial_statements_raw`, `financial_ratios`.
3. Add document tables: `filings`, `filing_pages`, `chart_series`.
4. Add discovery: `company_themes`, `company_web_endpoints`.
5. Add news: `news_articles`.
6. Add portfolio: `users`, `portfolios`, `holdings`, `transactions`, `portfolio_metrics`.
7. Add chat: `chat_sessions`, `chat_messages`, `user_uploads`.
8. Add system: `etl_runs`, `system_config`.

---

## Next Steps

- Define SQLAlchemy models matching this schema.
- Create Alembic migrations for version control.
- Set up connection pooling and read replicas for scale.
- Consider partitioning large tables (`financial_statements_raw`, `chat_messages`) by date ranges.

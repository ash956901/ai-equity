# Ingestion & ETL Pipelines – AI Equity Research Platform

## Overview

This document specifies the **crawling and ETL pipelines** for autonomously ingesting Indian equity data from NSE/BSE, company investor relations sites, news sources, and complex documents (PDFs, PPTs with tables/charts).

---

## Design Principles

1. **Idempotency** – Every pipeline run can be safely retried; use document hashes and unique constraints to prevent duplicates.
2. **Autonomous discovery** – Crawlers automatically discover investor relations URLs without manual input.
3. **Asynchronous execution** – All heavy work runs in background workers (Celery/RQ/Arq); FastAPI only triggers and monitors jobs.
4. **Structured logging** – All runs logged to `etl_runs` table with status, duration, errors.
5. **Incremental updates** – Prefer delta updates over full re-crawls where possible.
6. **Resilience** – Handle failures gracefully; partial success is acceptable; failed items can be retried independently.

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Scheduler / Triggers                      │
│  - Cron jobs (daily/weekly)                                  │
│  - Manual triggers via FastAPI                               │
│  - On-demand company refresh requests                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Background Worker Queue                     │
│              (Celery / RQ / Arq + Redis)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬─────────────┐
        ▼             ▼             ▼             ▼
   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐
   │  NSE   │   │  BSE   │   │   IR   │   │  News  │
   │Crawler │   │Crawler │   │Crawler │   │Fetcher │
   └────┬───┘   └────┬───┘   └────┬───┘   └────┬───┘
        │            │            │            │
        └────────────┴────────────┴────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │    Document Parser Queue     │
        │  (PDF/PPT/Table/Chart)       │
        └─────────────┬───────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │    Embedding & Vector DB     │
        └─────────────┬───────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │   Theme Tagging (Offline)    │
        └─────────────────────────────┘
```

---

## 1. NSE/BSE Filing Crawler

### Purpose
Fetch regulatory filings from NSE and BSE for all tracked companies.

### Sources
- **NSE**: Corporate announcements, financial results, annual reports
  - URL pattern: `https://www.nseindia.com/api/corporates-corporateActions?index=equities&symbol={SYMBOL}`
  - URL pattern: `https://www.nseindia.com/companies-listing/corporate-filings-announcements`
- **BSE**: Corporate announcements, financial results
  - URL pattern: `https://www.bseindia.com/corporates/ann.aspx?scrip={SCRIP_CODE}`

### Technology Stack
- **Scrapy** for HTML crawling
- **Playwright** only if JS rendering is required (NSE API calls)
- **requests** with session management for API endpoints

### Pipeline Steps

#### Step 1: Fetch Filing List
```python
# Pseudocode
for company in companies:
    filings_list = fetch_nse_filings(company.ticker_nse, since_date)
    for filing_meta in filings_list:
        if not exists_in_db(filing_meta.document_hash):
            queue_filing_download(filing_meta)
```

#### Step 2: Download Documents
```python
# Celery task
@celery.task
def download_filing(filing_meta):
    pdf_bytes = download_file(filing_meta.url)
    document_hash = sha256(pdf_bytes)
    
    # Upload to S3/Blob
    raw_uri = upload_to_s3(
        bucket='equity-filings',
        key=f'raw/nse/{company_id}/{filing_date}/{document_hash}.pdf',
        data=pdf_bytes
    )
    
    # Insert to DB
    filing = Filing(
        company_id=filing_meta.company_id,
        exchange_id=nse_exchange_id,
        filing_type=detect_filing_type(filing_meta.title),
        title=filing_meta.title,
        filing_date=filing_meta.date,
        source_url=filing_meta.url,
        raw_uri=raw_uri,
        document_hash=document_hash,
        status='pending'
    )
    db.add(filing)
    db.commit()
    
    # Queue for parsing
    queue_document_parser(filing.id)
```

#### Step 3: Detect Filing Type
```python
def detect_filing_type(title: str) -> str:
    title_lower = title.lower()
    if 'annual report' in title_lower:
        return 'Annual_Report'
    elif 'quarterly results' in title_lower or 'q1' in title_lower:
        return 'Quarterly_Results'
    elif 'investor presentation' in title_lower:
        return 'Presentation'
    elif 'concall' in title_lower or 'earnings call' in title_lower:
        return 'Concall'
    elif 'press release' in title_lower:
        return 'Press_Release'
    else:
        return 'Other'
```

### Scheduling
- **Daily**: Check for new filings for all active companies
- **On-demand**: User triggers refresh for specific company

### Idempotency
- Use `document_hash` (SHA-256 of file content) as unique key
- Skip download if hash already exists in DB

---

## 2. Investor Relations Site Crawler

### Purpose
Autonomously discover and crawl company investor relations pages for additional documents not available on exchanges.

### Auto-Discovery Strategy

#### Step 1: Seed Domain Discovery
```python
# For each company without ir_page_url
def discover_ir_page(company):
    base_domain = company.website_domain
    if not base_domain:
        # Try Google search: "{company_name} investor relations"
        search_results = google_search(f'{company.name} investor relations site:in')
        base_domain = extract_domain(search_results[0])
        company.website_domain = base_domain
        db.commit()
    
    # Probe common IR paths
    candidate_paths = [
        '/investor-relations',
        '/investors',
        '/financials',
        '/ir',
        '/investor',
        '/shareholders',
        '/corporate/investors'
    ]
    
    for path in candidate_paths:
        url = f'https://{base_domain}{path}'
        if is_valid_ir_page(url):
            save_endpoint(company.id, base_domain, path, 'investor_relations')
            company.ir_page_url = url
            db.commit()
            break
```

#### Step 2: Sitemap Parsing
```python
def parse_sitemap(base_domain):
    sitemap_urls = [
        f'https://{base_domain}/sitemap.xml',
        f'https://{base_domain}/sitemap_index.xml'
    ]
    
    for sitemap_url in sitemap_urls:
        try:
            sitemap = fetch_and_parse_sitemap(sitemap_url)
            ir_urls = filter_ir_urls(sitemap.urls)
            for url in ir_urls:
                save_endpoint_if_new(company.id, base_domain, url, 'auto_discovered')
        except:
            continue
```

#### Step 3: Validation Heuristics
```python
def is_valid_ir_page(url: str) -> bool:
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return False
        
        content = response.text.lower()
        keywords = [
            'investor relations',
            'financial results',
            'annual report',
            'quarterly results',
            'investor presentation',
            'shareholding pattern'
        ]
        
        # Check if at least 2 keywords present
        matches = sum(1 for kw in keywords if kw in content)
        return matches >= 2
    except:
        return False
```

### Crawling Strategy

#### Step 1: Fetch IR Page Links
```python
@celery.task
def crawl_ir_page(company_id, endpoint_id):
    endpoint = db.query(CompanyWebEndpoint).get(endpoint_id)
    url = f'https://{endpoint.base_domain}{endpoint.endpoint_path}'
    
    # Use Scrapy or BeautifulSoup
    soup = BeautifulSoup(requests.get(url).text, 'html.parser')
    
    # Find all PDF/PPTX links
    doc_links = soup.find_all('a', href=re.compile(r'\.(pdf|pptx?)$', re.I))
    
    for link in doc_links:
        doc_url = urljoin(url, link['href'])
        doc_title = link.get_text(strip=True) or link.get('title', 'Untitled')
        
        # Queue download
        queue_ir_document_download(company_id, doc_url, doc_title)
    
    # Update last crawled timestamp
    endpoint.last_crawled_at = datetime.now()
    db.commit()
```

#### Step 2: Download & Store
```python
@celery.task
def download_ir_document(company_id, doc_url, doc_title):
    doc_bytes = download_file(doc_url)
    document_hash = sha256(doc_bytes)
    
    # Check if already exists
    if db.query(Filing).filter_by(document_hash=document_hash).first():
        return  # Skip duplicate
    
    # Detect file type
    file_ext = doc_url.split('.')[-1].lower()
    
    # Upload to S3
    raw_uri = upload_to_s3(
        bucket='equity-filings',
        key=f'raw/ir/{company_id}/{document_hash}.{file_ext}',
        data=doc_bytes
    )
    
    # Insert to DB
    filing = Filing(
        company_id=company_id,
        filing_type=detect_filing_type(doc_title),
        title=doc_title,
        filing_date=extract_date_from_title(doc_title) or date.today(),
        source_url=doc_url,
        raw_uri=raw_uri,
        document_hash=document_hash,
        status='pending'
    )
    db.add(filing)
    db.commit()
    
    # Queue for parsing
    queue_document_parser(filing.id)
```

### Scheduling
- **Weekly**: Crawl all validated IR endpoints
- **On-demand**: User triggers company-specific refresh

---

## 3. Document Parser Pipeline

### Purpose
Extract text, tables, and charts from PDFs and PPTs.

### Technology Stack
- **PDFs**: PyMuPDF (fitz), pdfplumber, `unstructured`
- **PPTs**: `python-pptx`
- **Tables**: `camelot-py`, `tabula-py`, pdfplumber
- **OCR**: Tesseract (fallback for scanned docs)
- **Vision**: OpenAI GPT-4V, Google Gemini, or Azure Computer Vision for chart extraction

### Pipeline Steps

#### Step 1: PDF Text Extraction
```python
@celery.task
def parse_pdf(filing_id):
    filing = db.query(Filing).get(filing_id)
    pdf_bytes = download_from_s3(filing.raw_uri)
    
    # Extract text with layout preservation
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    pages_data = []
    
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text('text')
        has_tables = detect_tables_in_page(page)
        has_charts = detect_images_in_page(page)
        
        pages_data.append({
            'page_number': page_num,
            'text': text,
            'has_tables': has_tables,
            'has_charts': has_charts
        })
        
        # Save page metadata
        filing_page = FilingPage(
            filing_id=filing_id,
            page_number=page_num,
            text_content=text,
            has_tables=has_tables,
            has_charts=has_charts
        )
        db.add(filing_page)
    
    # Save full parsed text to S3
    parsed_text_uri = upload_json_to_s3(
        bucket='equity-filings',
        key=f'parsed/{filing.company_id}/{filing.id}.json',
        data={'pages': pages_data}
    )
    
    filing.parsed_text_uri = parsed_text_uri
    filing.status = 'parsed'
    db.commit()
    
    # Queue table extraction
    if any(p['has_tables'] for p in pages_data):
        queue_table_extraction(filing_id)
    
    # Queue chart extraction
    if any(p['has_charts'] for p in pages_data):
        queue_chart_extraction(filing_id)
    
    # Queue embedding
    queue_embedding(filing_id)
```

#### Step 2: Table Extraction
```python
@celery.task
def extract_tables(filing_id):
    filing = db.query(Filing).get(filing_id)
    pdf_bytes = download_from_s3(filing.raw_uri)
    
    # Use pdfplumber for table detection
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            
            for table_idx, table in enumerate(tables):
                # Convert to DataFrame
                df = pd.DataFrame(table[1:], columns=table[0])
                
                # Detect if financial statement
                if is_financial_statement(df):
                    parse_and_store_financial_statement(
                        company_id=filing.company_id,
                        filing_id=filing_id,
                        df=df,
                        page_num=page_num
                    )
                else:
                    # Store as generic statement_items
                    store_generic_table(
                        company_id=filing.company_id,
                        filing_id=filing_id,
                        df=df,
                        page_num=page_num
                    )
```

#### Step 3: Financial Statement Normalization
```python
def parse_and_store_financial_statement(company_id, filing_id, df, page_num):
    # Detect statement type (P&L, Balance Sheet, Cash Flow)
    statement_type = detect_statement_type(df)
    
    # Extract period information from headers
    periods = extract_periods_from_columns(df.columns)
    
    # Normalize line items
    for _, row in df.iterrows():
        line_item = normalize_line_item(row[0])
        
        for period, col_name in zip(periods, df.columns[1:]):
            value = parse_financial_value(row[col_name])
            
            if value is not None:
                stmt = FinancialStatementRaw(
                    company_id=company_id,
                    source_filing_id=filing_id,
                    statement_type=statement_type,
                    period_start=period['start'],
                    period_end=period['end'],
                    fiscal_year=period['fiscal_year'],
                    quarter=period.get('quarter'),
                    line_item=line_item,
                    value=value,
                    currency='INR',
                    unit='Cr'  # Detect from document
                )
                db.add(stmt)
    
    db.commit()
    
    # Queue ratio calculation
    queue_ratio_calculation(company_id, periods[-1]['end'])
```

#### Step 4: Chart Extraction
```python
@celery.task
def extract_charts(filing_id):
    filing = db.query(Filing).get(filing_id)
    pdf_bytes = download_from_s3(filing.raw_uri)
    
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    
    for page_num, page in enumerate(doc, start=1):
        images = page.get_images()
        
        for img_idx, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image['image']
            
            # Filter by size (likely charts are > 50KB)
            if len(image_bytes) < 50000:
                continue
            
            # Upload image to S3
            chart_uri = upload_to_s3(
                bucket='equity-filings',
                key=f'charts/{filing.company_id}/{filing.id}/page{page_num}_img{img_idx}.png',
                data=image_bytes
            )
            
            # Queue vision analysis
            queue_chart_vision_analysis(
                company_id=filing.company_id,
                filing_id=filing_id,
                chart_uri=chart_uri,
                page_num=page_num
            )
```

#### Step 5: Vision-Based Chart Analysis
```python
@celery.task
def analyze_chart_with_vision(company_id, filing_id, chart_uri, page_num):
    image_bytes = download_from_s3(chart_uri)
    
    # Call vision LLM (e.g., GPT-4V, Gemini)
    prompt = """
    Analyze this chart/graph and extract:
    1. Chart type (bar, line, pie, etc.)
    2. Title or metric name
    3. X-axis labels and values
    4. Y-axis labels and values
    5. All data series with their values
    6. Units (if visible)
    
    Return as structured JSON.
    """
    
    response = vision_llm.analyze(
        image=image_bytes,
        prompt=prompt
    )
    
    chart_data = json.loads(response)
    
    # Store structured data
    for series in chart_data.get('series', []):
        for point in series['data']:
            chart_series = ChartSeries(
                company_id=company_id,
                source_filing_id=filing_id,
                chart_image_uri=chart_uri,
                metric_name=chart_data['title'],
                category=series['name'],
                period=parse_date(point['label']),
                label=point['label'],
                value=point['value'],
                unit=chart_data.get('unit', ''),
                extraction_confidence=response.confidence
            )
            db.add(chart_series)
    
    db.commit()
```

#### Step 6: PPT/PPTX Parsing
```python
@celery.task
def parse_pptx(filing_id):
    filing = db.query(Filing).get(filing_id)
    pptx_bytes = download_from_s3(filing.raw_uri)
    
    prs = Presentation(io.BytesIO(pptx_bytes))
    slides_data = []
    
    for slide_num, slide in enumerate(prs.slides, start=1):
        # Extract text
        text_content = []
        for shape in slide.shapes:
            if hasattr(shape, 'text'):
                text_content.append(shape.text)
        
        # Extract tables
        for shape in slide.shapes:
            if shape.has_table:
                table = shape.table
                df = extract_table_from_pptx(table)
                store_generic_table(filing.company_id, filing_id, df, slide_num)
        
        # Extract charts/images
        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                image = shape.image
                image_bytes = image.blob
                
                chart_uri = upload_to_s3(
                    bucket='equity-filings',
                    key=f'charts/{filing.company_id}/{filing.id}/slide{slide_num}.png',
                    data=image_bytes
                )
                
                queue_chart_vision_analysis(
                    filing.company_id, filing_id, chart_uri, slide_num
                )
        
        slides_data.append({
            'slide_number': slide_num,
            'text': '\n'.join(text_content)
        })
    
    # Save parsed text
    parsed_text_uri = upload_json_to_s3(
        bucket='equity-filings',
        key=f'parsed/{filing.company_id}/{filing.id}.json',
        data={'slides': slides_data}
    )
    
    filing.parsed_text_uri = parsed_text_uri
    filing.status = 'parsed'
    db.commit()
    
    # Queue embedding
    queue_embedding(filing_id)
```

---

## 4. News Ingestion Pipeline

### Purpose
Fetch and analyze news articles related to Indian equities.

### Sources
- **GNews API**: `https://gnews.io/api/v4/search?q={company_name}&country=in`
- **NewsAPI**: `https://newsapi.org/v2/everything?q={ticker}`
- **Google News RSS**: `https://news.google.com/rss/search?q={company_name}+stock`

### Pipeline Steps

#### Step 1: Fetch News
```python
@celery.task
def fetch_company_news(company_id):
    company = db.query(Company).get(company_id)
    
    # Build search queries
    queries = [
        f'{company.name} stock',
        f'{company.ticker_nse} NSE',
        f'{company.ticker_bse} BSE'
    ]
    
    for query in queries:
        # GNews
        articles = gnews_api.search(query, country='in', max_results=10)
        for article in articles:
            process_news_article(company_id, article)
        
        # NewsAPI
        articles = newsapi.search(query, language='en', from_date=date.today() - timedelta(days=7))
        for article in articles:
            process_news_article(company_id, article)
```

#### Step 2: Deduplicate & Store
```python
def process_news_article(company_id, article):
    # Check if already exists
    if db.query(NewsArticle).filter_by(source_url=article['url']).first():
        return  # Skip duplicate
    
    news = NewsArticle(
        company_id=company_id,
        headline=article['title'],
        body=article.get('description') or article.get('content', ''),
        source=article['source']['name'],
        source_url=article['url'],
        published_at=parse_datetime(article['publishedAt']),
        tickers=extract_tickers(article['title'] + ' ' + article.get('description', ''))
    )
    db.add(news)
    db.commit()
    
    # Queue sentiment analysis
    queue_sentiment_analysis(news.id)
```

#### Step 3: Sentiment Analysis
```python
@celery.task
def analyze_sentiment(news_id):
    news = db.query(NewsArticle).get(news_id)
    
    # Combine headline and body
    text = f"{news.headline}. {news.body}"
    
    # Use FinBERT or similar
    sentiment = finbert_model.predict(text)
    
    # India-specific rules
    impact_level = 'Medium'
    affected_dimension = 'general'
    
    # Rule-based enhancement
    if 'sebi' in text.lower() or 'regulatory' in text.lower():
        affected_dimension = 'regulation'
        impact_level = 'High'
    elif 'earnings' in text.lower() or 'results' in text.lower():
        affected_dimension = 'earnings'
        impact_level = 'High'
    elif 'management' in text.lower() or 'ceo' in text.lower():
        affected_dimension = 'management'
    
    # Update news record
    news.sentiment_score = sentiment['score']
    news.sentiment_label = sentiment['label']
    news.impact_level = impact_level
    news.affected_dimension = affected_dimension
    news.relevance_confidence = sentiment['confidence']
    
    db.commit()
```

### Scheduling
- **Hourly**: Fetch news for companies in user portfolios
- **Daily**: Fetch news for all active companies

---

## 5. Embedding & Vector DB Pipeline

### Purpose
Generate embeddings for all parsed documents and store in vector DB for semantic search.

### Technology Stack
- **Embedding model**: OpenAI `text-embedding-3-small`, Cohere, or open-source alternatives
- **Vector DB**: Qdrant or pgvector (see next document)

### Pipeline Steps

#### Step 1: Chunk Documents
```python
@celery.task
def embed_filing(filing_id):
    filing = db.query(Filing).get(filing_id)
    parsed_data = download_json_from_s3(filing.parsed_text_uri)
    
    # Chunk text (500-1000 tokens per chunk with overlap)
    chunks = []
    for page in parsed_data.get('pages', []):
        page_chunks = chunk_text(
            text=page['text'],
            chunk_size=800,
            overlap=100
        )
        
        for chunk_idx, chunk_text in enumerate(page_chunks):
            chunks.append({
                'text': chunk_text,
                'metadata': {
                    'company_id': str(filing.company_id),
                    'filing_id': str(filing.id),
                    'filing_type': filing.filing_type,
                    'filing_date': filing.filing_date.isoformat(),
                    'page_number': page['page_number'],
                    'chunk_index': chunk_idx
                }
            })
    
    # Generate embeddings
    embeddings = embedding_model.embed([c['text'] for c in chunks])
    
    # Store in vector DB
    vector_ids = []
    for chunk, embedding in zip(chunks, embeddings):
        vector_id = vector_db.upsert(
            collection='company_filings',
            vector=embedding,
            payload=chunk['metadata'],
            text=chunk['text']
        )
        vector_ids.append(vector_id)
    
    # Update filing_pages with vector IDs
    # (group by page_number and update)
    
    filing.status = 'embedded'
    db.commit()
```

---

## 6. Theme Tagging (Offline Agent)

### Purpose
Periodically analyze all company data to detect hidden themes and subdomain exposure.

### Pipeline Steps

#### Step 1: Aggregate Company Context
```python
@celery.task
def tag_company_themes(company_id):
    company = db.query(Company).get(company_id)
    
    # Gather context
    recent_filings = db.query(Filing).filter_by(
        company_id=company_id
    ).order_by(Filing.filing_date.desc()).limit(5).all()
    
    filing_texts = [download_json_from_s3(f.parsed_text_uri) for f in recent_filings]
    
    # Query vector DB for key themes
    theme_keywords = [
        'artificial intelligence', 'AI', 'machine learning',
        'data center', 'cloud computing',
        'electric vehicle', 'EV', 'battery',
        'defense', 'aerospace',
        'renewable energy', 'solar', 'wind',
        'blockchain', 'cryptocurrency'
    ]
    
    detected_themes = []
    
    for theme in theme_keywords:
        # Semantic search in vector DB
        results = vector_db.search(
            collection='company_filings',
            query_text=theme,
            filter={'company_id': str(company_id)},
            limit=5
        )
        
        if results and results[0].score > 0.7:
            # LLM reasoning
            reasoning = llm.generate(
                prompt=f"""
                Company: {company.name}
                Theme: {theme}
                Evidence: {results[0].text}
                
                Explain if and how this company has exposure to the theme.
                Classify exposure as: direct, indirect, supply_chain, or customer.
                Rate impact score 0.0-1.0.
                """
            )
            
            detected_themes.append({
                'theme': theme,
                'reasoning': reasoning,
                'confidence': results[0].score
            })
    
    # Store themes
    for theme_data in detected_themes:
        theme = CompanyTheme(
            company_id=company_id,
            theme_name=normalize_theme_name(theme_data['theme']),
            exposure_type=extract_exposure_type(theme_data['reasoning']),
            confidence_score=theme_data['confidence'],
            impact_score=extract_impact_score(theme_data['reasoning']),
            reasoning=theme_data['reasoning'],
            validated_by='theme_tagging_agent'
        )
        db.add(theme)
    
    db.commit()
```

### Scheduling
- **Weekly**: Run theme tagging for all companies with new filings
- **Monthly**: Full refresh for all companies

---

## 7. ETL Orchestration & Monitoring

### Celery Task Graph

```python
# Example: Full company refresh
@celery.task
def refresh_company_data(company_id):
    # Log ETL run
    etl_run = ETLRun(
        pipeline_name='full_company_refresh',
        run_type='on_demand',
        company_id=company_id,
        status='running',
        started_at=datetime.now()
    )
    db.add(etl_run)
    db.commit()
    
    try:
        # Chain tasks
        chain(
            fetch_nse_filings.s(company_id),
            fetch_bse_filings.s(company_id),
            crawl_ir_page.s(company_id),
            fetch_company_news.s(company_id),
            tag_company_themes.s(company_id)
        ).apply_async()
        
        etl_run.status = 'completed'
        etl_run.completed_at = datetime.now()
    except Exception as e:
        etl_run.status = 'failed'
        etl_run.error_message = str(e)
    finally:
        etl_run.duration_seconds = (datetime.now() - etl_run.started_at).total_seconds()
        db.commit()
```

### Monitoring Dashboard (FastAPI Endpoints)

```python
@app.get('/api/etl/status')
def get_etl_status():
    recent_runs = db.query(ETLRun).order_by(
        ETLRun.started_at.desc()
    ).limit(50).all()
    
    return {
        'recent_runs': [run.to_dict() for run in recent_runs],
        'active_tasks': celery_app.control.inspect().active(),
        'scheduled_tasks': celery_app.control.inspect().scheduled()
    }

@app.post('/api/etl/trigger/{company_id}')
def trigger_company_refresh(company_id: UUID):
    task = refresh_company_data.delay(company_id)
    return {'task_id': task.id, 'status': 'queued'}
```

---

## Summary

This ingestion architecture provides:

1. **Autonomous discovery** of investor relations sites
2. **Idempotent** pipeline runs with hash-based deduplication
3. **Complex document parsing** (PDFs, PPTs, tables, charts)
4. **Vision-based chart extraction** for hidden insights
5. **Real-time news ingestion** with sentiment analysis
6. **Offline theme tagging** for discovery features
7. **Comprehensive monitoring** and on-demand refresh capabilities

All pipelines are designed to scale to 50k+ companies and handle millions of documents efficiently.

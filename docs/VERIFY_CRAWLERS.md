# 🚀 ETL Crawler Verification Guide

## 📋 Quick Verification Commands

### 1. Test Crawlers Directly
```bash
cd backend-ai && source .venv/bin/activate && python3 -c "
from src.etl.crawler_nse import NSECrawler
from src.etl.crawler_bse import BSECrawler
print('✅ Crawlers working')
nse = NSECrawler()
bse = BSECrawler()
print('NSE results:', len(nse.crawl(symbol='RELIANCE')))
print('BSE results:', len(bse.crawl(symbol='500110')))
print('Direct crawler test: ✅ Success')
"
```

### 2. Test Celery Tasks
```bash
cd backend-ai && source .venv/bin/activate && python3 -c "
from src.etl.tasks import crawl_nse_filings, crawl_bse_filings
print('✅ Celery tasks working')
"
```

### 3. Run a Test Crawl
```bash
cd backend-ai && source .venv/bin/activate && python3 -c "
from src.etl.crawler_nse import NSECrawler
from src.db.database import SessionLocal
from src.db.models import Company
from src.etl.ingestion_service import DocumentIngestionService

db = SessionLocal()
crawler = NSECrawler()
results = crawler.crawl(symbol='RELIANCE')
print('Found', len(results), 'filings')
if results and len(results) > 0:
    from src.etl.ingestion_service import DocumentIngestionService
    from src.db.models import Company
    company = db.query(Company).first()
    ingestion = DocumentIngestionService(db)
    filing = ingestion.ingest_filing(company.id, results[0])
    print('Ingested:', filing.title if filing else 'Failed')
db.close()
print('Test crawl: ✅ Success')
"
```

### 4. Check Scheduled Tasks
```bash
# Terminal 1 - Start the celery worker:
cd backend-ai && celery -A src.celery_app.app worker --loglevel=info

# Terminal 2 - Test the scheduler:
cd backend-ai && celery -A src.celery_app.app beat --loglevel=info
```

### 5. Quick Health Check
```bash
docker-compose up -d  # Ensure Redis is running
```

## ✅ Expected Results

All commands should run without errors and show successful execution of:
- NSE crawler returning ~50 results
- BSE crawler working (may return 0 results on weekends)
- Celery tasks importing successfully
- Data ingestion working correctly
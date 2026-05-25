import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import logging
from src.etl.commodity_sync_task import sync_commodity_prices
from src.etl.event_monitor_task import monitor_geopolitical_events
from src.etl.news_sync_task import sync_news
from src.etl.tasks import crawl_nse_filings
from src.etl.seed_causal_data import main as seed_causal

logging.basicConfig(level=logging.INFO)

print("--- 1. Seeding Causal Data ---")
try:
    seed_causal()
except Exception as e:
    print(f"Error seeding causal data: {e}")

print("\n--- 2. Syncing Commodity Prices ---")
try:
    res = sync_commodity_prices()
    print("Result:", res)
except Exception as e:
    print(f"Error: {e}")

print("\n--- 3. Monitoring Geopolitical Events ---")
try:
    res = monitor_geopolitical_events()
    print("Result:", res)
except Exception as e:
    print(f"Error: {e}")

print("\n--- 4. Syncing News ---")
try:
    res = sync_news()
    print("Result:", res)
except Exception as e:
    print(f"Error: {e}")

print("\n--- 5. Crawling NSE Filings (Top Companies) ---")
try:
    # Just crawl for Reliance to get some data quickly
    crawl_nse_filings(symbol="RELIANCE")
    print("Crawled NSE filings.")
except Exception as e:
    print(f"Error: {e}")

print("\n--- Pipeline Run Complete ---")

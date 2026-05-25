import sys
import logging
from pathlib import Path

# Ensure the backend-ai directory is in the Python path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.etl.commodity_sync_task import sync_commodity_prices
from src.etl.event_monitor_task import monitor_geopolitical_events
from src.etl.news_sync_task import sync_news
from src.etl.seed_causal_data import main as seed_causal

# Suppress overly verbose logs from httpx
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
    print("\n========================================================")
    print("🚀 EQUITY AI - DAILY DATA UPDATE PIPELINE")
    print("========================================================\n")

    print("--- 1. Seeding Base Causal Data ---")
    try:
        seed_causal()
        print("✅ Base causal chains & exposures seeded.\n")
    except Exception as e:
        print(f"❌ Error seeding causal data: {e}\n")

    print("--- 2. Syncing Live Commodity Prices ---")
    try:
        res = sync_commodity_prices()
        print(f"✅ Synced Oil/Gas prices. Errors (if any): {len(res.get('errors', []))}\n")
    except Exception as e:
        print(f"❌ Error syncing commodities: {e}\n")

    print("--- 3. Monitoring Global Geopolitical Events (GDELT) ---")
    try:
        res = monitor_geopolitical_events()
        print(f"✅ Saved {res.get('events_saved', 0)} new significant events.\n")
    except Exception as e:
        print(f"❌ Error monitoring events: {e}\n")

    print("--- 4. Syncing Market News & Sentiment ---")
    try:
        res = sync_news()
        print(f"✅ Synced and classified {res.get('news_saved', 0)} new financial headlines.\n")
    except Exception as e:
        print(f"❌ Error syncing news: {e}\n")

    print("========================================================")
    print("🎉 DAILY UPDATE COMPLETE! The database is now current.")
    print("========================================================\n")

if __name__ == "__main__":
    main()

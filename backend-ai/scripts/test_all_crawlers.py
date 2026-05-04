"""Comprehensive test for all 6 new ETL crawlers.

Tests:
  1. AMFI NAV        — amfiindia.com/spages/NAVAll.txt
  2. mfapi.in        — api.mfapi.in/mf
  3. data.gov.in     — MCA company master
  4. RBI macro       — rbi.org.in current rates
  5. NSE Bhavcopy    — nsearchives daily OHLCV
  6. ET/Mint RSS     — financial news feeds
"""

import sys
import os
import logging
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s %(name)s: %(message)s",
)
# Suppress noisy urllib3 retries
logging.getLogger("urllib3").setLevel(logging.WARNING)

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"


def divider(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# 1. AMFI NAV
# ---------------------------------------------------------------------------
def test_amfi():
    divider("1. AMFI NAV Crawler")
    from src.etl.crawler_amfi import AMFICrawler

    crawler = AMFICrawler()
    data = crawler.crawl()
    count = len(data)
    print(f"  Total schemes fetched: {count}")

    if count > 0:
        print(f"  {PASS} AMFI — {count} schemes")
        sample = data[0]
        print(f"  Sample: {sample['scheme_code']} | {sample['scheme_name'][:60]} | NAV: {sample['nav']} | {sample['date']}")

        # Test filtering
        hdfc = crawler.crawl(fund_house="HDFC")
        print(f"  HDFC filter: {len(hdfc)} schemes")
    else:
        print(f"  {FAIL} AMFI — no data")

    return count > 0


# ---------------------------------------------------------------------------
# 2. mfapi.in
# ---------------------------------------------------------------------------
def test_mfapi():
    divider("2. mfapi.in Crawler")
    from src.etl.crawler_mfapi import MFApiCrawler

    crawler = MFApiCrawler()

    # List schemes
    schemes = crawler.list_schemes()
    print(f"  Total schemes listed: {len(schemes)}")

    if not schemes:
        print(f"  {FAIL} mfapi — cannot list schemes")
        return False

    # Fetch detail for one scheme
    code = schemes[0]["schemeCode"]
    detail = crawler.get_scheme_detail(code)
    if detail and detail.get("data"):
        meta = detail.get("meta", {})
        nav_count = len(detail["data"])
        print(f"  {PASS} mfapi — scheme {code}")
        print(f"  Fund: {meta.get('fund_house', 'N/A')}")
        print(f"  Name: {meta.get('scheme_name', 'N/A')[:60]}")
        print(f"  NAV records: {nav_count}")
        print(f"  Latest: {detail['data'][0]}")
        return True
    else:
        print(f"  {FAIL} mfapi — no detail for scheme {code}")
        return False


# ---------------------------------------------------------------------------
# 3. data.gov.in
# ---------------------------------------------------------------------------
def test_datagov():
    divider("3. data.gov.in MCA Crawler")
    from src.etl.crawler_datagov import DataGovCrawler

    crawler = DataGovCrawler()

    # Discovery (no API key needed)
    datasets = crawler.discover_datasets(search="company master", limit=10)
    count = len(datasets)
    print(f"  Datasets discovered: {count}")

    if count > 0:
        print(f"  {PASS} data.gov.in — {count} MCA datasets found")
        for ds in datasets[:3]:
            print(f"    • {ds['title'][:60]}")
            print(f"      resource_id: {ds['resource_id']}")
        print(f"  ℹ️  Full record access requires free API key from data.gov.in")
        return True
    else:
        print(f"  {FAIL} data.gov.in — no datasets found")
        return False


# ---------------------------------------------------------------------------
# 4. RBI
# ---------------------------------------------------------------------------
def test_rbi():
    divider("4. RBI Macro Crawler")
    from src.etl.crawler_rbi import RBICrawler

    crawler = RBICrawler()
    data = crawler.crawl()

    rates = data.get("policy_rates", {})
    table = data.get("key_rates_table", [])
    print(f"  Policy rates: {len(rates)} indicators")
    print(f"  Table rows: {len(table)}")

    if rates:
        print(f"  {PASS} RBI — {len(rates)} rates")
        for k, v in list(rates.items())[:5]:
            print(f"    {k}: {v}")
        return True
    else:
        print(f"  {FAIL} RBI — no rates extracted")
        return False


# ---------------------------------------------------------------------------
# 5. NSE Bhavcopy
# ---------------------------------------------------------------------------
def test_nse_bhavcopy():
    divider("5. NSE Bhavcopy Crawler")
    from src.etl.crawler_nse_bhavcopy import NSEBhavcopycrawler

    crawler = NSEBhavcopycrawler()

    # Fetch latest
    data = crawler.crawl()
    count = len(data)
    print(f"  Total records (EQ): {count}")

    if count > 0:
        print(f"  {PASS} NSE Bhavcopy — {count} stocks")
        # Find RELIANCE
        reliance = [r for r in data if r["symbol"] == "RELIANCE"]
        if reliance:
            r = reliance[0]
            print(f"  RELIANCE: O={r['open']} H={r['high']} L={r['low']} C={r['close']} V={r['volume']} Del%={r['delivery_pct']}")
        else:
            print(f"  (RELIANCE not in today's EQ bhavcopy)")

        # Show date
        print(f"  Date: {data[0].get('date', 'N/A')}")
        return True
    else:
        print(f"  {FAIL} NSE Bhavcopy — no data (market may be closed)")
        return False


# ---------------------------------------------------------------------------
# 6. ET/Mint RSS
# ---------------------------------------------------------------------------
def test_news_rss():
    divider("6. News RSS Crawler (ET + Mint)")
    from src.etl.crawler_news_rss import NewsRSSCrawler

    crawler = NewsRSSCrawler()
    articles = crawler.crawl()
    count = len(articles)
    print(f"  Total articles: {count}")

    if count > 0:
        print(f"  {PASS} News RSS — {count} articles")

        # Group by feed
        by_feed = {}
        for a in articles:
            by_feed.setdefault(a["feed_name"], []).append(a)

        for feed_name, items in by_feed.items():
            print(f"\n  [{feed_name}] — {len(items)} articles")
            for item in items[:3]:
                title = item["title"][:70]
                pub = item.get("pub_date", "N/A")
                if pub and len(pub) > 19:
                    pub = pub[:19]
                print(f"    • {title}")
                print(f"      {pub} | {item['link'][:60]}...")

        return True
    else:
        print(f"  {FAIL} News RSS — no articles")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    results = {}

    results["AMFI NAV"] = test_amfi()
    results["mfapi.in"] = test_mfapi()
    results["data.gov.in"] = test_datagov()
    results["RBI"] = test_rbi()
    results["NSE Bhavcopy"] = test_nse_bhavcopy()
    results["News RSS"] = test_news_rss()

    divider("SUMMARY")
    for name, passed in results.items():
        icon = PASS if passed else FAIL
        print(f"  {icon} {name}")

    total = sum(results.values())
    print(f"\n  {total}/{len(results)} crawlers passed")

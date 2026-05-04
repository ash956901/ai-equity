"""Test script for the new SEBI and MCA crawlers."""

import logging
import sys
import os
from pprint import pprint

# Add backend-ai to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.etl.crawler_sebi import SEBICrawler
from src.etl.crawler_mca import MCACrawler

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def test_sebi():
    print("--- Testing SEBI Crawler ---")
    crawler = SEBICrawler()
    results = crawler.crawl(symbol="RELIANCE", since_date="2023-01-01")
    print(f"SEBI Results Count: {len(results)}")
    if results:
        print("Sample Result:")
        pprint(results[0])
    else:
        print("No results or failed (expected if blocked).")
    print()

def test_mca():
    print("--- Testing MCA Crawler ---")
    crawler = MCACrawler()
    results = crawler.crawl(symbol="RELIANCE", since_date="2023-01-01")
    print(f"MCA Results Count: {len(results)}")
    if results:
        print("Sample Result:")
        pprint(results[0])
    else:
        print("No results or failed (expected if blocked).")
    print()

if __name__ == "__main__":
    test_sebi()
    test_mca()

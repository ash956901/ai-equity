import sys
import os
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.etl.crawler_screener import ScreenerCrawler

logging.basicConfig(level=logging.INFO)

def main():
    crawler = ScreenerCrawler()
    print("Fetching data for RELIANCE...")
    data = crawler.crawl("RELIANCE")
    
    # Just print some high-level keys to verify the data was extracted
    print(f"\n--- Results for {data.get('symbol')} ---")
    print(f"Company Meta Keys: {list(data.get('meta', {}).keys())}")
    if 'meta' in data and 'company_name' in data['meta']:
        print(f"Company Name: {data['meta']['company_name']}")
    
    print(f"\nP&L Data Metrics: {list(data.get('profit_loss', {}).get('data', {}).keys())}")
    
    # Print a sample from P&L (e.g. Sales)
    sales = data.get('profit_loss', {}).get('data', {}).get('Sales\xa0+', {})
    if not sales:
        sales = data.get('profit_loss', {}).get('data', {}).get('Sales', {})
    print(f"P&L Sales: {sales}")
    
    # Print some documents
    docs = data.get('documents', {})
    print(f"\nDocuments:")
    print(f"  Annual Reports: {len(docs.get('annual_reports', []))}")
    print(f"  Concalls: {len(docs.get('concalls', []))}")
    print(f"  Credit Ratings: {len(docs.get('credit_ratings', []))}")
    print(f"  Announcements: {len(docs.get('announcements', []))}")

if __name__ == "__main__":
    main()

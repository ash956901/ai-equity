"""
One-time setup: creates Shamanth's portfolio with diverse Indian holdings.
Run from backend-ai directory:
    python scripts/setup_shamanth_portfolio.py
"""

import sys
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src.db.database import SessionLocal
from src.db.models import Company, Holding, Portfolio, User

# ── Additional companies (those not already seeded by seed_db.py) ─────────────
NEW_COMPANIES = [
    # Automobile / EV
    {"name": "Tata Motors", "ticker_nse": "TATAMOTORS", "ticker_bse": "500570", "isin": "INE155A01022",
     "sector": "Automobile", "industry": "Commercial & Passenger Vehicles", "market_cap_inr": 290000,
     "description": "India's largest auto company; owns Jaguar Land Rover globally."},
    # Pharma
    {"name": "Dr Reddy's Laboratories", "ticker_nse": "DRREDDY", "ticker_bse": "500124", "isin": "INE089A01023",
     "sector": "Healthcare", "industry": "Generic Pharmaceuticals", "market_cap_inr": 100000,
     "description": "Leading Indian pharma with strong generics and biosimilars pipeline."},
    # Metals
    {"name": "Hindalco Industries", "ticker_nse": "HINDALCO", "ticker_bse": "500440", "isin": "INE038A01020",
     "sector": "Materials", "industry": "Aluminum & Copper", "market_cap_inr": 135000,
     "description": "World's largest aluminum rolling company; subsidiary Novelis is a global leader."},
    {"name": "Tata Steel", "ticker_nse": "TATASTEEL", "ticker_bse": "500470", "isin": "INE081A01020",
     "sector": "Materials", "industry": "Steel", "market_cap_inr": 180000,
     "description": "One of India's largest steel manufacturers with global operations."},
    # Cement
    {"name": "UltraTech Cement", "ticker_nse": "ULTRACEMCO", "ticker_bse": "532538", "isin": "INE481G01011",
     "sector": "Materials", "industry": "Cement", "market_cap_inr": 310000,
     "description": "India's largest cement manufacturer with 120+ MTPA capacity."},
    # Power
    {"name": "NTPC", "ticker_nse": "NTPC", "ticker_bse": "532555", "isin": "INE733E01010",
     "sector": "Energy", "industry": "Power Generation", "market_cap_inr": 370000,
     "description": "India's largest power utility; expanding into renewables."},
    {"name": "Power Grid Corporation of India", "ticker_nse": "POWERGRID", "ticker_bse": "532898",
     "isin": "INE752E01010", "sector": "Energy", "industry": "Power Transmission", "market_cap_inr": 285000,
     "description": "Central transmission utility managing inter-state power."},
    # Oil & Gas
    {"name": "ONGC", "ticker_nse": "ONGC", "ticker_bse": "500312", "isin": "INE213A01029",
     "sector": "Energy", "industry": "Oil & Gas Exploration", "market_cap_inr": 340000,
     "description": "India's largest oil and gas exploration company (PSU)."},
]

# ── Portfolio holdings: (ticker_nse, quantity, avg_price_inr) ─────────────────
HOLDINGS = [
    # IT / Technology
    ("TCS",         15,  3850.0),
    ("INFY",        25,  1580.0),
    ("HCLTECH",     20,  1650.0),
    # Banking (Private)
    ("HDFCBANK",    40,  1700.0),
    ("ICICIBANK",   50,  1100.0),
    ("AXISBANK",    35,   990.0),
    # Banking (PSU)
    ("SBIN",        80,   760.0),
    # Oil & Gas / Energy
    ("RELIANCE",    15,  2900.0),
    ("ONGC",        60,   270.0),
    ("NTPC",        80,   355.0),
    # Pharma
    ("SUNPHARMA",   20,  1700.0),
    ("DRREDDY",      8,  1280.0),
    # FMCG
    ("HINDUNILVR",  10,  2450.0),
    ("ITC",         80,   430.0),
    # Automobile
    ("MARUTI",       5, 11500.0),
    ("TATAMOTORS",  30,   900.0),
    # Metals
    ("TATASTEEL",   60,   155.0),
    ("HINDALCO",    45,   620.0),
    # Telecom
    ("BHARTIARTL",  20,  1450.0),
    # Cement
    ("ULTRACEMCO",   6, 10800.0),
    # Infrastructure
    ("LT",           8,  3600.0),
]


def main():
    db = SessionLocal()
    try:
        # ── 1. Find Shamanth's user (by email, as seeded) ────────────────────
        user = db.query(User).filter(User.email == "shamanth.hiremath.101@gmail.com").first()
        if not user:
            print("ERROR: User not found. Run seed_db.py first, or update the email.")
            return

        # Update profile fields
        user.full_name = "Shamanth M Hiremath"
        user.username = "shamzzz"
        user.phone_number = "+918660857769"
        user.expertise_level = "beginner"
        user.risk_tolerance = "moderate"
        user.investment_horizon = "medium"
        db.flush()
        print(f"[~] User: {user.full_name}  UUID: {user.id}")

        # ── 2. Add new companies (skip if ISIN already exists) ───────────────
        existing_isins = {c.isin for c in db.query(Company.isin).all() if c.isin}
        ticker_to_id: dict[str, uuid.UUID] = {
            c.ticker_nse: c.id for c in db.query(Company).filter(Company.ticker_nse.isnot(None)).all()
        }

        for cd in NEW_COMPANIES:
            if cd["isin"] in existing_isins:
                print(f"  (skip) {cd['ticker_nse']} — ISIN already in DB")
                ticker_to_id[cd["ticker_nse"]] = (
                    db.query(Company.id).filter(Company.isin == cd["isin"]).scalar()
                )
                continue
            c = Company(
                id=uuid.uuid4(),
                name=cd["name"],
                ticker_nse=cd["ticker_nse"],
                ticker_bse=cd.get("ticker_bse"),
                isin=cd["isin"],
                sector=cd.get("sector"),
                industry=cd.get("industry"),
                market_cap_inr=cd.get("market_cap_inr"),
                description=cd.get("description"),
                listing_status="active",
            )
            db.add(c)
            db.flush()
            ticker_to_id[cd["ticker_nse"]] = c.id
            print(f"  [+] Added: {cd['ticker_nse']} — {cd['name']}")

        # ── 3. Create primary portfolio ───────────────────────────────────────
        portfolio = (
            db.query(Portfolio)
            .filter(Portfolio.user_id == user.id, Portfolio.is_primary == True)
            .first()
        )
        if not portfolio:
            portfolio = Portfolio(
                id=uuid.uuid4(),
                user_id=user.id,
                name="Shamanth's Portfolio",
                description="Diversified Indian equity portfolio: IT, Banking, FMCG, Auto, Pharma, Metals, Energy, Telecom, Cement, Infrastructure.",
                is_primary=True,
                broker="Zerodha",
            )
            db.add(portfolio)
            db.flush()
            print(f"[+] Created portfolio: {portfolio.name} ({portfolio.id})")
        else:
            print(f"[~] Portfolio exists: {portfolio.name} ({portfolio.id})")

        # ── 4. Add holdings ───────────────────────────────────────────────────
        added = skipped = missing = 0
        for ticker, qty, avg_price in HOLDINGS:
            company_id = ticker_to_id.get(ticker)
            if not company_id:
                print(f"  [!] {ticker} not in DB — skipping")
                missing += 1
                continue
            existing = db.query(Holding).filter(
                Holding.portfolio_id == portfolio.id,
                Holding.company_id == company_id,
            ).first()
            if existing:
                skipped += 1
                continue
            db.add(Holding(
                id=uuid.uuid4(),
                portfolio_id=portfolio.id,
                company_id=company_id,
                quantity=qty,
                average_price=avg_price,
                current_price=round(avg_price * 1.08, 2),
                currency="INR",
            ))
            added += 1

        db.commit()
        print(f"\n[OK] Holdings: {added} added, {skipped} already existed, {missing} missing")
        print("\n" + "=" * 60)
        print("SETUP COMPLETE")
        print("=" * 60)
        print(f"User UUID : {user.id}")
        print(f"Portfolio : {portfolio.id}")
        print(f"\n-> Open browser DevTools Console and run:")
        print(f"  localStorage.setItem('equityai-user-id', '{user.id}')")
        print(f"\n-> Then reload the app to see your profile and portfolio.")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

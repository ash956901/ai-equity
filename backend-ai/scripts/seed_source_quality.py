"""Seed the ``source_quality`` table with sane defaults.

Run from the repo root:

    cd backend-ai
    python -m scripts.seed_source_quality
"""

import logging

from src.db.database import init_db
from src.etl.confidence import seed_source_quality
from src.etl.sector_commodity_loader import seed_sector_commodity_links
from src.etl.theme_taxonomy_loader import seed_theme_taxonomy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")


def main() -> None:
    init_db()
    print("Seeding source_quality...")
    print(seed_source_quality())
    print("Seeding theme_taxonomy...")
    print(seed_theme_taxonomy())
    print("Seeding sector_commodity_links...")
    print(seed_sector_commodity_links())


if __name__ == "__main__":
    main()

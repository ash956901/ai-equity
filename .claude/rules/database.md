# Subsystem: Database

## Stack
- Primary Store: **PostgreSQL** + **SQLAlchemy** schemas.
- Indexing Store: **Qdrant** (self-hosted).

## Rules
- Qdrant is handling vector payload ops for exact `company_filings` mappings with `nomic-embed-text` (768 dimensions).
- Any modifications to the Postgres database structure must be processed through Alembic.
  - Review `alembic/versions/` for exact DB change state.
  - Test seed files (`scripts/seed_db.py`) exist to rebuild relationships for development.
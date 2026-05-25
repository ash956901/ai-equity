# Subsystem: Backend API

## Infrastructure
- **FastAPI** drives the backend endpoints.
- Total of ~21 working endpoints spanning 11 domains (chat, companies, portfolio, compare, timeline, screens, auth/users, alerts).

## Rules
- When testing functionality, refer to `docs/BACKEND_TESTING_GUIDE.md`.
- Background worker execution relies on Celery (`celery_app.py`, etc.). Task routing goes through RabbitMQ or Redis as configured.
- Authentication currently uses simple UUID in localStorage for demo purposes. Ensure endpoints account for this and don't prematurely block demo access awaiting proper JWT mapping unless requested.
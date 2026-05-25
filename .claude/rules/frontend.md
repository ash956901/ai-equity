# Subsystem: Frontend

## Tech Stack
- **Vite** + **React** + **TypeScript**.
- Styling handled by **Tailwind CSS**.

## Structure
- 10 main views are built.
- UI wiring focuses on interacting closely with standard FastAPI CRUD routes.

## Rules
- Standard API wiring uses components in `src/`. Ensure TypeScript typing matches FastAPI schema validation.
- Mock authentication is implemented with `localStorage` holding a user UUID to emulate auth. Keep it intact unless rebuilding the full authentication flow.
# AGENT.md - AI Coding Agent Guidelines

## Commands
- **Frontend**: `cd frontend && npm run dev` (dev), `npm run build` (build), `npm run lint` (lint)
- **Backend**: `cd backend && python -m uvicorn app.main:app --reload` (dev), `pip install -r requirements.txt` (deps)
- **Testing**: No test framework configured yet. Recommend adding pytest for backend, vitest for frontend

## Architecture
- **Stack**: FastAPI backend + React/TypeScript frontend with WebSocket communication
- **Database**: PostgreSQL with SQLAlchemy ORM, Redis for job queue
- **AI**: LangGraph agents with OpenAI/Anthropic for web scraping automation
- **Browser**: Stagehand/browser-use for automated web interactions
- **Structure**: `backend/app/` (API, models, agents, queue), `frontend/src/` (React components, stores)

## Code Style
- **Backend**: Python with Pydantic models, async/await, type hints, SQLAlchemy relationships
- **Frontend**: TypeScript, ESLint config, Tailwind CSS, Zustand for state management
- **Imports**: Relative imports in backend (`from ..db`), absolute from root in frontend
- **Naming**: snake_case (Python), camelCase (TypeScript), PascalCase (React components)
- **Models**: SQLAlchemy declarative base, JSONB for complex data, relationship mappings
- **WebSockets**: Global manager pattern, JSON message types, error handling with disconnect cleanup
- **Environment**: Use `.env` files, Pydantic Settings for configuration management

## Database Commands
- **Connect**: `psql -U web_scraper_user -d web_scraper_db`
- **View Data**: `psql -U web_scraper_user -d web_scraper_db -c "SELECT * FROM scrape_jobs ORDER BY created_at DESC LIMIT 10;"`
- **Reset DB**: `psql -U web_scraper_user -d web_scraper_db -c "TRUNCATE scrape_jobs, form_fields, websites RESTART IDENTITY CASCADE;"`

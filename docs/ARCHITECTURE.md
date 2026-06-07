# Architecture — V1

## Recommended stack

### Backend
- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- Alembic
- PostgreSQL
- httpx
- pytest
- Ruff
- mypy

### Frontend
- TypeScript
- React
- Vite
- TanStack Query
- TanStack Table
- React Hook Form
- Zod
- Vitest
- Playwright

### Runtime
- Docker Compose
- Separate API and worker processes
- PostgreSQL-backed persistent jobs for V1

## Why this stack

Python is well suited to:
- tolerant JSON / CSV parsing;
- structured validation;
- asynchronous gateway calls;
- LLM integrations;
- rapid backend iteration.

TypeScript is well suited to:
- typed UI contracts;
- tables and filters;
- safe form handling;
- predictable frontend maintenance.

## Important V1 constraint

Do **not** use FastAPI `BackgroundTasks` for persistent evaluations. A process restart can lose in-memory work.

Use:
- a database jobs table;
- a separate worker process;
- transactional job claiming;
- retry counters;
- persisted state.

Redis, Celery, Dramatiq, or a dedicated queue may be introduced later if scale requires them. Avoid adding infrastructure before the persistent Postgres-backed worker is insufficient.

## Suggested repository layout

```text
.
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── PRD.md
│   ├── FEATURES.yaml
│   ├── ARCHITECTURE.md
│   └── DECISIONS.md
├── fixtures/
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── parsers/
│   │   ├── services/
│   │   ├── workers/
│   │   └── main.py
│   └── tests/
└── frontend/
    ├── package.json
    ├── src/
    └── tests/
```

## Separation of concerns

- `parsers/`: source-specific parsing and normalization.
- `models/`: internal persistence models.
- `services/judge/`: Judge interface, Portkey adapter, mock adapter.
- `workers/`: persisted jobs, retries, resume behavior.
- `api/`: transport only; no parsing logic embedded in route handlers.
- `frontend/`: UI only; no secret handling.

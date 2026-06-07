# Repository instructions for Codex

## Source of truth
Read before planning or editing:
- `docs/PRD.md`
- `docs/FEATURES.yaml`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`

## Working rules
- Implement one feature ID from `docs/FEATURES.yaml` at a time.
- Before editing, state the selected feature, affected files, risks, and verification plan.
- Do not silently expand scope.
- Preserve raw imported payloads.
- Treat automated Judge disagreements as suspected issues, not confirmed FP/FN.
- The Judge must never receive source verdict, source score, or source reasoning.
- Keep secrets backend-only. Never log API keys.
- Do not use in-memory background tasks for persisted evaluation jobs.
- Ask before adding a new production dependency.

## Verification
For every completed feature:
- add or update tests;
- run formatter, lint, type checks, and relevant tests;
- review the diff for regressions and secret leakage;
- update the feature status only after acceptance criteria pass;
- summarize changed files and remaining risks.

## Preferred stack
- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL, httpx, pytest, Ruff, mypy.
- Frontend: TypeScript, React, Vite, TanStack Query, TanStack Table, Zod, Vitest, Playwright.

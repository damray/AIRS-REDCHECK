# AI Response Threat Evaluator — V1 Agent Pack

This pack is a documentation-first starter kit for building the V1 application.

## Start here

1. Copy these files into a new Git repository.
2. Read `docs/PRD.md`, `docs/FEATURES.yaml`, and `docs/ARCHITECTURE.md`.
3. Run Claude Code in plan mode with `prompts/01-plan-only.md`.
4. Review the proposed plan.
5. Use Codex or Claude Code as the single implementation agent for one feature slice at a time with `prompts/03-implement-one-feature.md`.
6. Use the other tool as an independent reviewer with `prompts/04-review-current-diff.md`.

## Recommended first milestone

Implement the smallest end-to-end vertical slice:

- Docker Compose with PostgreSQL
- FastAPI health endpoint
- static JSON import
- agent JSON import
- normalized stream / attempt persistence
- parser unit tests
- minimal import summary API

Do not start with the dashboard or the Portkey integration before the normalization layer is covered by tests.

## Backend development

```bash
cd backend
ruff format .
ruff check .
mypy app tests
pytest
```

## Docker Compose

```bash
docker compose up --build
curl -i http://localhost:8000/health
```

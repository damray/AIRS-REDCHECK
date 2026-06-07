# AI Response Threat Evaluator — V1 Agent Pack

This pack is a documentation-first starter kit for building the V1 application.


## Product objective

Build a platform that imports AI red-teaming exports, independently re-evaluates whether each **model response** is harmful, illegal, unsafe, or non-compliant, and helps analysts identify disagreements between a source evaluator and a new LLM-as-a-Judge.

The platform evaluates the **model output**, not whether the original prompt is malicious.

## Core principle

The new Judge need to understand the context of the target, for this each analyst can create is own system prompt for the llm as a judge. based on that, the llm as judge will categorize the **model output**

Automated comparison produces:
- agreements;
- suspected source false positives;
- suspected source false negatives;
- uncertain cases;
- technical evaluation errors.

Only human adjudication produces confirmed TP, TN, FP, and FN metrics.

## Deployment

This repository ships with a Docker Compose deployment for the V1 stack:

- PostgreSQL on port `5432`
- FastAPI backend on port `8000`
- persistent evaluation worker
- Vite frontend on port `5173`

### Prerequisites

- Docker and Docker Compose
- A Portkey gateway profile created in the app before running real Judge evaluations

### Start the stack

```bash
docker compose up --build
```

The backend container runs Alembic migrations before starting the API. The worker
starts separately and resumes persisted evaluation jobs from PostgreSQL.

### Verify deployment

```bash
curl -i http://localhost:8000/health
```

Open the web UI at:

```text
http://localhost:5173
```

### Configuration

Use `.env.example` as the reference for local environment values. Keep real
secrets out of Git; Portkey API keys are configured through backend APIs and are
masked in UI-facing responses.

For production, replace the default Compose database password, keep PostgreSQL
storage on a persistent volume, and run the API and worker as separate processes.

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

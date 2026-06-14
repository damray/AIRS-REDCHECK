# AI Response Threat Evaluator — V1 Agent Pack

This pack is a documentation-first starter kit for building the V1 application.


## Product objective

Build a platform that imports AI red-teaming exports, independently re-evaluates whether each **model response** is harmful, illegal, unsafe, or non-compliant, and helps analysts identify disagreements between a source evaluator and a new LLM-as-a-Judge.

The platform evaluates the **model output**, not whether the original prompt is malicious.

![alt text](image.png)

![alt text](image-1.png)

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

`MAX_UPLOAD_BYTES` controls the maximum CSV or JSON import size. The default
Docker Compose configuration allows uploads up to 100 MiB.

For production, replace the default Compose database password, keep PostgreSQL
storage on a persistent volume, and run the API and worker as separate processes.

## Application menu

The left navigation separates operational work from setup work.

### Triage

Shows the automated comparison summary after Judge evaluation. Use it to monitor
processed attempts, remaining attempts, agreements, disagreements, uncertain
cases, and evaluation errors. These numbers are triage signals only; they are
not confirmed quality metrics.

### Review

Contains the analyst review queue. Use it to inspect source output, Judge
verdict, comparison status, attempt detail, and agent timelines. Analysts can
confirm the source verdict, confirm the Judge verdict, mark the response as an
alarm threat, and add reviewer comments. Alarm threat means the model response
is not acceptable but is expected to have low business impact. This is the
quality-control step that turns automated signals into adjudicated cases.

The `Review required` filter shows attempts that still need a human decision.
Its count decreases as decisions are saved. A checked review box marks attempts
that already have an adjudication decision. Use the `Alarm threat` filter to
show low-impact unacceptable responses that were reviewed with that decision.

### Quality

Shows reviewed quality metrics only after human adjudication. Accuracy,
precision, recall, F1, and the confusion matrix are computed from reviewed
cases, with the human-confirmed verdict treated as ground truth. Alarm threat
reviews count as low-impact threat verdicts.

### Export

Downloads CSV working sets. Use presets for normalized results, disagreements,
or reviewed cases, or build a filtered export by comparison status, verdict,
input type, review state, review decision such as `ALARM_THREAT`, and text
search.

### Datasets

Imports CSV or JSON red-team exports, shows import summaries and parsing errors,
and starts evaluation jobs. Static exports and agent exports are normalized into
streams and attempts while preserving the raw imported payload. Upload size is
controlled by `MAX_UPLOAD_BYTES`; the default Docker Compose value is 100 MiB.

### Judge config

Creates Portkey gateway profiles and Judge prompt profiles. Configure model
routing, timeout, temperature, system prompt, and rubric here before running
evaluation jobs. Portkey secrets stay backend-only and are masked in UI-facing
responses.

## Recommended workflow

Use a repeatable process. The quality of the final metrics depends on consistent
configuration, clean imports, and disciplined human review.

1. Configure the Judge in `Judge config`.
   Create or select a Portkey gateway profile, save the API key, choose routing
   by provider slug or config ID, set the Judge model, then create a prompt
   profile. The prompt and rubric should describe the target context and make it
   explicit that the Judge evaluates the model output, not the source label.

2. Import data in `Datasets`.
   Upload a CSV or JSON export and check the import summary. Review parsing
   errors before running evaluations, because bad normalization will reduce the
   usefulness of the review queue. Valid records are still imported when other
   records fail.

3. Run evaluation from `Datasets`.
   Select the dataset, Portkey profile, and prompt profile, then start the
   evaluation job. The worker persists jobs in PostgreSQL, retries temporary
   failures, and can resume after restart.

4. Monitor results in `Triage`.
   Watch processing progress, disagreements, uncertain cases, and evaluation
   errors. Treat automated disagreements as suspected issues. A source-stricter
   or Judge-stricter status is a review priority, not a confirmed false positive
   or false negative.

5. Adjudicate in `Review`.
   Work through disagreements, uncertain cases, and evaluation errors. For each
   case, inspect the model output first, then the prompt and metadata context.
   Confirm the source verdict, confirm the Judge verdict, or mark the case
   as an alarm threat when the response is unacceptable but low impact. Add
   comments when the decision depends on policy interpretation, target context,
   or missing evidence.

6. Check impact in `Quality`.
   Use reviewed quality metrics only after enough cases have been adjudicated.
   Track review coverage alongside precision, recall, F1, and the confusion
   matrix; low coverage can make the metrics misleading.

7. Export working sets from `Export`.
   Export reviewed cases for audit trails, disagreements for follow-up, or a
   filtered subset for policy calibration. Keep exported files under the same
   data-handling controls as the original red-team payloads.

For best results, calibrate the Judge prompt on a small reviewed sample before
processing large datasets, keep the same prompt profile for comparable runs, and
separate technical evaluation errors from safety disagreements.

## Scripts

The `scripts/get_report_or_token.py` helper can fetch an AIRS Red Team bearer
token, list available scans, and download a selected report. Downloaded archives,
JSON files, and CSV files are written under `scripts/reports/`, which is ignored
by Git because reports can contain sensitive prompts and outputs.

Required credentials:

- `TSG_ID`
- `CLIENT_ID`
- `CLIENT_SECRET`

Run with environment variables:

```bash
export TSG_ID=...
export CLIENT_ID=...
export CLIENT_SECRET=...
python scripts/get_report_or_token.py
```

Run with a vault-backed environment file, for example with 1Password:

```bash
op run --env-file=.env.oauth -- python scripts/get_report_or_token.py
```

Useful options:

```bash
# Download the selected report as CSV instead of JSON.
python scripts/get_report_or_token.py --csv

# Print only the bearer token, for reuse in another command.
python scripts/get_report_or_token.py --token-only

# Include diagnostic request and token-claim details.
python scripts/get_report_or_token.py --debug
```

Never commit credential files or downloaded reports. Keep `.env.oauth` and other
local secret files outside Git, and keep downloaded report payloads in
`scripts/reports/` or another ignored location.

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

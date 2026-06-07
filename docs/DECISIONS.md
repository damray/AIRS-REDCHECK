# Architecture Decision Log

Record decisions here when implementation reveals a trade-off.

## ADR-001 — Normalize static and agent exports into stream / attempt

**Status:** accepted

A static record is one stream with one attempt.  
An agent record is one stream with multiple attempts.

This avoids maintaining two downstream evaluation pipelines.

## ADR-002 — Human review required for confirmed FP/FN

**Status:** accepted

Automated Judge disagreement is triage, not ground truth.  
Confirmed quality metrics are computed only from human-adjudicated cases.

## ADR-003 — Separate worker process with persisted jobs

**Status:** accepted

Long-running LLM evaluation must survive API process restarts.  
V1 uses PostgreSQL-backed persistent jobs before adding Redis or a queue broker.

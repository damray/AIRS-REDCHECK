# Product Requirements Document — AI Response Threat Evaluator V1

## 1. Product objective

Build a platform that imports AI red-teaming exports, independently re-evaluates whether each **model response** is harmful, illegal, unsafe, or non-compliant, and helps analysts identify disagreements between a source evaluator and a new LLM-as-a-Judge.

The platform evaluates the **model output**, not whether the original prompt is malicious.

## 2. Core principle

The new Judge is not ground truth.

Automated comparison produces:
- agreements;
- suspected source false positives;
- suspected source false negatives;
- uncertain cases;
- technical evaluation errors.

Only human adjudication produces confirmed TP, TN, FP, and FN metrics.

## 3. Supported input shapes

### 3.1 Static attack export

Required source fields:
- `prompt`
- `output`
- `threat`

Optional metadata:
- `asr`
- `severity`
- `category`
- `sub_category`
- `goal_category`
- `dasf_v2`
- `nist`
- `owasp`
- `mitre_atlas`
- `multi_turn`
- `generation`
- `turn`
- `multi_turn_prompt`

### 3.2 Agent attack export

Required stream-level source fields:
- `goal`
- `stream_id`
- `stream_threat`
- one or more `iteration_N` fields

Each `iteration_N` value is a serialized JSON string that may contain:
- `iteration`
- `prompt`
- `output`
- `score`
- `judge_reasoning`
- `threat`
- `techniques`
- `improvement`
- `prompts_objective`
- `summary`

## 4. Internal normalized model

Every imported record becomes:

```text
Project workspace
└── Dataset import
    └── Stream
        └── Attempt
            ├── Source evaluator result
            ├── Independent Judge result
            └── Optional human review
```

A static record is represented as one stream containing one attempt.

An agent record is represented as one stream containing multiple attempts.

A project workspace is a user-facing container for one or more dataset imports.
It provides a stable label for a customer, application, assessment, campaign, or
test run without changing the preserved raw imported payloads.

A dataset import can also have a user-facing scan name so an uploaded file can
be renamed independently from its project workspace.

## 5. V1 functional scope

### FR-001 Upload CSV or JSON
- Upload CSV.
- Upload JSON arrays.
- Accept a single JSON object for local test convenience.
- Preserve the raw imported payload.

### FR-002 Format detection
- Detect static exports using `prompt`, `output`, `threat`.
- Detect agent exports using `goal`, `stream_id`, `stream_threat`, and `iteration_N`.
- Support flat custom mapping for unrecognized CSV or flat JSON files.

### FR-003 Robust normalization
- Normalize all supported files into streams and attempts.
- Continue importing valid records when some records fail.
- Expose import counts and downloadable parsing errors.
- Preserve raw values and normalized values when normalizing metadata.

### FR-004 Blind Judge evaluation
The Judge receives:
- original prompt;
- model output;
- goal for agent streams;
- evaluation rubric.

The Judge must not receive:
- source threat verdict;
- source score;
- source reasoning;
- previous source judgments.

### FR-005 Structured Judge output
The Judge returns:
- `response_verdict`: `THREAT`, `SAFE`, or `UNCERTAIN`;
- `confidence`: number from 0 to 1;
- `response_behavior`: `SAFE_REFUSAL`, `SAFE_REDIRECT`, `SAFE_COMPLETION`, `UNSAFE_COMPLETION`, or `AMBIGUOUS`;
- `risk_category`;
- `explanation`;
- optional `evidence_excerpt`.

### FR-006 Comparison engine
Generate:
- `AGREEMENT_THREAT`;
- `AGREEMENT_SAFE`;
- `SOURCE_STRICTER_THAN_JUDGE`;
- `JUDGE_STRICTER_THAN_SOURCE`;
- `REVIEW_REQUIRED`;
- `EVALUATION_ERROR`.

### FR-007 Lightweight human adjudication
On disagreements and uncertain cases:
- confirm source verdict;
- confirm Judge verdict;
- mark alarm threat when the model response is not acceptable but has low expected business impact;
- add comment;
- record reviewer and timestamp.

### FR-008 Portkey gateway profile
Required:
- profile name;
- gateway base URL;
- Portkey API key;
- routing mode;
- provider slug or config ID;
- Judge model.

Optional:
- legacy virtual key;
- timeout;
- metadata tags.

Secrets must remain backend-only and never appear in logs.

### FR-009 Resilient run execution
- Persist jobs before processing.
- Track `PENDING`, `RUNNING`, `RETRYING`, `COMPLETED`, `FAILED`.
- Retry temporary failures with limits.
- Resume after restart.
- Re-run only failed attempts.
- Track latency, token usage, and cost when available.

### FR-010 Automated triage dashboard
Display:
- total streams;
- total attempts;
- processed and remaining attempts;
- errors;
- agreements;
- disagreements;
- source stricter than Judge;
- Judge stricter than source;
- uncertain;
- review required;
- agent/static split;
- average attempts per stream.

### FR-011 Reviewed quality dashboard
Display metrics only on human-reviewed cases:
- reviewed cases;
- review coverage;
- confirmed TP;
- confirmed TN;
- confirmed FP;
- confirmed FN;
- accuracy;
- precision;
- recall;
- F1 score.

### FR-012 Result explorer
Filters:
- static / agent;
- stream ID;
- agreement / disagreement;
- source stricter;
- Judge stricter;
- uncertain;
- reviewed / not reviewed;
- review decision;
- threat / safe;
- severity;
- category;
- technique.

Agent streams expose an attempt timeline.

### FR-013 Evaluation error drilldown
Automated triage error counts must be actionable.

Required:
- the Automated triage Errors metric links into the main results workflow;
- clicking Errors filters the result table to `EVALUATION_ERROR`;
- error rows show the source prompt and model output context;
- safe error code, message, and timestamp are visible in the attempt detail
  panel;
- users can clear the error filter and return to the normal result view.

Constraints:
- do not add a separate dashboard error mini-table for V1;
- do not expose raw gateway responses by default;
- do not expose secrets, headers, API keys, or raw provider request payloads;
- label these rows as technical evaluation failures, not confirmed safety
  verdicts.

### FR-014 Automatic storage and history
Persist:
- dataset;
- mapping profile;
- parser version;
- Judge system prompt;
- prompt version hash;
- model and inference configuration;
- Portkey profile reference;
- results;
- errors;
- metrics;
- timestamps.

### FR-015 Export
- normalized attempts CSV;
- normalized attempts JSON;
- full JSON report;
- disagreements CSV;
- reviewed cases CSV.

### FR-016 Prompt and output search
Analysts need to find imported attempts by terms in the stored source prompt and
model output.

Required:
- search source prompts;
- search source outputs;
- search both fields with one query;
- combine search with existing result explorer filters;
- preserve pagination;
- return the same normalized result shape as the result explorer.

Initial implementation:
- use server-side substring matching over `attempts.source_prompt` and
  `attempts.source_output`;
- expose API query parameters such as `source_prompt_contains`,
  `source_output_contains`, and `q`;
- add UI controls in the result explorer.

Scale path:
- measure query latency on realistic imported datasets before adding database
  indexes;
- for substring or fuzzy matching, add PostgreSQL `pg_trgm` and GIN indexes on
  `source_prompt` and `source_output`;
- for language-aware token search and ranking, add generated `tsvector` columns
  or expression indexes using PostgreSQL full-text search;
- keep search read-only and avoid modifying preserved raw payloads;
- keep export and search result downloads paginated or streamed for large
  result sets.

### FR-017 Security controls
- encrypted secret storage or external secret injection;
- secrets masked in UI;
- no secrets in logs;
- file size limit;
- malformed file protections;
- dataset deletion;
- concurrency limit;
- server-side validation.

### FR-018 Project workspaces for scan imports
Analysts need to organize uploaded scan results by project so multiple imports
do not become one undifferentiated result set.

Required:
- create or select a project workspace during JSON or CSV upload;
- create a default project name from filename and timestamp when the user does
  not provide one;
- associate every dataset import with exactly one project workspace;
- assign every dataset import a user-facing scan name;
- rename a scan import without mutating the preserved raw imported payload;
- list project workspaces with import counts and latest activity timestamp;
- rename a project workspace without mutating imported raw payloads;
- delete or archive a project workspace with explicit handling for contained
  datasets, evaluations, reviews, import errors, and jobs;
- scope dashboards, result explorer filters, import errors, evaluation jobs, and
  exports by project workspace.

Initial deletion behavior:
- implement project deletion as soft delete or archive for V1 so evaluation
  history and human reviews are not accidentally destroyed;
- hide archived projects from default list and result views;
- require an explicit later feature before adding permanent hard delete.

## 6. Explicit V1 non-goals

- multi-Judge voting;
- model debate;
- agentic implementation workflows inside the product;
- MITRE / OWASP / NIST / EU AI Act recalculation;
- JSONPath editor;
- arbitrary nested transformation designer;
- PDF reporting;
- full benchmark suite.

Existing compliance metadata is imported and filterable but not recalculated.

## 7. Decisions still to validate with real exports

- Is `stream_threat` always a logical OR across attempt-level `threat` values?
- What is the exact source meaning and scale of `score`?
- What is the exact source meaning of `asr`?
- Are metadata list fields always serialized strings, or can they be JSON arrays?

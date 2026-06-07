# Repository instructions for Claude Code

Read the shared project documentation:
- @docs/PRD.md
- @docs/FEATURES.yaml
- @docs/ARCHITECTURE.md
- @docs/DECISIONS.md

## Working rules
- Implement one feature ID at a time.
- Use plan mode before any multi-file or architectural change.
- Before editing, identify affected files, risks, and validation commands.
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
- update feature status only after acceptance criteria pass;
- summarize changed files and remaining risks.

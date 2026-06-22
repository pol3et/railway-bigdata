# Railway Big Data Course Project - Agent Guide

Read this file first when working inside `bigdata/course_proj`.

## Project Goal

Build a course-project repository for railway data collection and analysis:

1. Gather data from selected web sources with a path to automatic updates.
2. Use a Big Data technology, with Spark/lakehouse integration as the preferred track.
3. Process and analyze stored data into practical findings.
4. Produce report and presentation evidence. Final score depends on processing depth and volume.

The local assignment prompt is `task.png`.

## Mandatory Workflow

This is a `bigdata/` coursework task. Before planning or editing:

1. Use `research-orchestrator`.
2. Research local files first.
3. Use routed MCP providers for external docs. For Spark/API claims, prefer Context7 or Ref.
4. Write/update `.planning/coursework/research/bigdata/<task-slug>.md`.
5. Update `docs/PROGRESS_LOG.md` and `.planning/COURSEWORK_PROGRESS.md` before stopping.
6. Do not claim a run, score, dataset, test, report result, or live integration unless there is executed output or a committed evidence artifact.

## Current Repository Shape

Current code now lives under one installable source tree:

| Path | Current role | Status |
|---|---|---|
| `src/railway_lakehouse/bronze/` | Raw ingestion package with MinIO landing, scheduler, Eurostat/World Bank/GDELT/RSS sources, and national/historical add-ons. | Implemented; KSH/Statistik Austria/UIC/history scheduling remains GAP-005. |
| `src/railway_lakehouse/silver/` | Stats normalization, LLM-bounded news extraction, schemas, Ollama client. | Core logic tested; storage reads/writes are not wired. |
| `src/railway_lakehouse/gold/` | Deterministic feature matrix builder and Parquet writer. | Core logic tested; Silver storage reads are not wired. |
| `src/railway_lakehouse/pipeline.py` | End-to-end orchestration skeleton with fixture-backed Bronze reads. | GAP-004 closed for deterministic local fixtures; live MinIO/Ollama/Spark path remains unproven. |
| `docs/GAP_REGISTER.md` | Owner-ready gap register and test failure mapping. | Current split point for classmates. |

Historical docs and `.planning/codebase/*.md` may mention `bigdata/course_proj/parser/`. That path is stale for the current tree unless it reappears in the filesystem.

## Documentation Map

Start here:

- `README.md` - project overview and status.
- `TASK.md` - course requirements mapped to local deliverables.
- `docs/INDEX.md` - documentation table of contents.
- `docs/CODEMAP.md` - file-by-file map of the current dump.
- `docs/ARCHITECTURE.md` - target architecture and data flow.
- `docs/DATA_CONTRACTS.md` - Bronze, Silver, Gold contracts.
- `docs/WORKSTREAMS.md` - ownership boundaries for parallel contributors.
- `docs/AGENTIC_WORKFLOW.md` - agent collaboration rules and handoff format.
- `docs/VERIFICATION.md` - checks and evidence requirements.
- `docs/ORGANIZATION_PLAN.md` - staged cleanup plan.
- `docs/PROGRESS_LOG.md` - single persistent findings/progress log.

## Agent Routing

Use this table to pick the right surface before editing:

| Work type | Read first | Primary paths | Do not touch unless needed |
|---|---|---|---|
| Project intake or planning | `TASK.md`, `docs/PROGRESS_LOG.md`, `docs/ORGANIZATION_PLAN.md` | Documentation only | Runtime source files |
| Bronze ingestion | `docs/CODEMAP.md`, `docs/DATA_CONTRACTS.md`, `WIRING.md` | `src/railway_lakehouse/bronze/` | Silver/Gold logic |
| Source parsers | `docs/WORKSTREAMS.md`, `docs/DATA_CONTRACTS.md` | `src/railway_lakehouse/bronze/sources/` | Existing Bronze landing contract |
| Silver preprocessing | `docs/SILVER_DESIGN.md`, `docs/DATA_CONTRACTS.md` | `src/railway_lakehouse/silver/` | Bronze raw collection |
| Feature audit | `docs/DATA_CONTRACTS.md`, `src/railway_lakehouse/silver/config.py` | `src/railway_lakehouse/silver/schema.py`, `src/railway_lakehouse/silver/news/`, `src/railway_lakehouse/silver/stats/` | Source fetch credentials |
| Gold analytics | `docs/ARCHITECTURE.md`, `docs/VERIFICATION.md` | `src/railway_lakehouse/gold/` | Bronze source adapters |
| Spark/lakehouse integration | `docs/ARCHITECTURE.md`, `docs/ORGANIZATION_PLAN.md` | future `spark/` or integration modules | Do not invent evidence |
| Report/presentation | `TASK.md`, `docs/PROGRESS_LOG.md`, `output/` evidence | `output/`, future `report/` | Core logic without a data need |

## Hard Rules

- Keep raw web data immutable in Bronze. Do not parse, filter, or normalize inside raw landing code.
- Keep numeric stats merging deterministic. LLMs may classify labels or extract article facts, but they must not rewrite numeric rows.
- Do not hardcode a course answer or fabricated dataset.
- Do not print or copy secrets. Mention variable names only.
- Do not move files or change imports without a written plan. The tree is already split; accidental moves can break relative imports.
- Put runtime outputs under `output/` or a documented lakehouse bucket/path, not next to source modules.
- Preserve user changes and do not revert unrelated files.

## Recommended Checks

Use targeted checks. Do not start long live collectors unless explicitly asked.

```bash
python -m compileall bigdata/course_proj
```

For future implementation, add project-local tests and document exact commands in `docs/VERIFICATION.md`.

## Handoff Template

When stopping, append to `docs/PROGRESS_LOG.md`:

```md
## YYYY-MM-DD - <short session title>

Status: <done | in progress | blocked>

Changed:
- <paths>

Findings:
- <facts backed by files or outputs>

Evidence:
- <commands, outputs, generated files>

Next:
- <concrete next step>
```

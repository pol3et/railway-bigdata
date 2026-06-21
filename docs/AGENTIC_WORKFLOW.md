# Agentic Workflow

## Start Checklist

1. Read `AGENTS.md`.
2. Read `README.md`, `TASK.md`, and `docs/PROGRESS_LOG.md`.
3. Run the required `research-orchestrator` workflow for any `bigdata/` edit.
4. Inspect current filesystem before trusting older planning docs.
5. Decide which workstream owns the task in `docs/WORKSTREAMS.md`.

## Collaboration Rules

- Work in the smallest owning surface that can solve the task.
- Keep source code, docs, generated output, and runtime scratch files separate.
- Record discoveries in `docs/PROGRESS_LOG.md` as they happen.
- Update `.planning/COURSEWORK_PROGRESS.md` before stopping.
- Do not silently pivot if an expected file, API, command, or dataset is missing.

## Evidence Rules

Use one of these evidence types before making a claim:

- local file contents,
- executed command output,
- generated artifact path,
- research log with cited URL,
- course prompt text/image.

Do not claim:

- a live source works unless it was run,
- a dataset exists unless it is present,
- tests pass unless the command was executed,
- Spark integration exists unless a Spark job exists and ran.

## Suggested Agent Handoff

Append this format to `docs/PROGRESS_LOG.md`:

```md
## YYYY-MM-DD - <session title>

Status: <done | in progress | blocked>

Files read:
- `<path>`

Files changed:
- `<path>`

Findings:
- <grounded finding>

Evidence:
- `<command>` -> <result>

Open questions:
- <question>

Next:
- <specific next action>
```

## Blocker Protocol

When blocked, stop and ask the user. Include:

- original path,
- blocker evidence,
- why continuing is risky,
- 2-4 options,
- recommended option.

Record the decision in both `docs/PROGRESS_LOG.md` and `.planning/COURSEWORK_PROGRESS.md`.

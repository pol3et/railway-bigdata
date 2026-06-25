# Opus review rubric — load-bearing PRs (opus-tier gaps)

> The orchestrator (Claude session) dispatches this as an **Opus** `ship-it:ship-reviewer` subagent
> (or `general-purpose`/`architect-reviewer` with `model: opus`) for any PR the runner parks
> `needs_opus_review` — i.e. a **LOAD-BEARING** PR that touches a `LOAD_BEARING_PATHS` core path
> (decided PER-PR from the impl verdict's `files_changed`, NOT a per-gap label; see
> `scripts/orch/night.config.sh` + `pr_is_load_bearing` in `run_wave.sh`). It is the merge gate for
> load-bearing work — a codex review is run too, but only as advisory input. **Fixes are always codex**
> (this reviewer never edits code; findings go back via `codex exec … resume`). Feed the subagent: this rubric, the gap's
> finalized spec (`output/evidence/orch/<gap>/spec.md` or `docs/GAP_TASKS.md`), the impl verdict
> (`output/evidence/orch/<gap>/verdict.json`), the advisory codex review
> (`output/evidence/orch/<gap>/review.json`), and the full PR diff (`gh pr diff <PR>`), plus access
> to the worktree `../wt-<gap>` to read changed files in context.

## What to judge (be a skeptic; assume green tests can hide gaps)

1. **DoD actually met in the PRODUCTION path** — not just in tests that inject helpers. The GAP-039
   miss is the template: a content-hash cache existed and unit tests passed, but the real pipeline
   never instantiated it, so the idempotency DoD was unmet. Trace the real entrypoint, not the test.
2. **Correctness & edge cases** — boundary values (e.g. a valid `0`/empty that truthiness drops),
   error/failure accounting, idempotency/determinism, backward compatibility with existing data.
3. **Tests are meaningful & deterministic** — they exercise the production path (not only mocked
   internals), cover the edge cases, and don't depend on `coursework/` data or live services
   (use `tmp_path`/fixtures). A regression test exists for each fixed defect.
4. **AGENTS.md Hard Rules** — raw Bronze immutable; numeric merges deterministic (no LLM-rewritten
   numbers); no fabricated data; outputs under `output/`; dashboard (`docs/index.html`/`TASKS.md`)
   kept in sync when pipeline state changed.
5. **Scope discipline** — the PR addresses this gap only; no unrelated churn.

## Output — ONLY this JSON (matches scripts/orch/schemas/review_findings.schema.json)

```json
{
  "verdict": "approve" | "request_changes",
  "summary": "one-paragraph judgement",
  "findings": [
    {"priority": "P1|P2|P3|P4", "title": "...", "location": "file:line", "why": "...", "fix": "concrete fix"}
  ],
  "contract_items_verified": ["which DoD/contract items you personally verified in the diff"]
}
```

## Merge gate (orchestrator applies)

Merge **only if** the impl verdict is clean (`verdict_clean`) AND the Opus verdict is `approve` with
**no P1/P2** finding (`review_clean`). Otherwise feed the findings back to the implementer thread
(`codex exec … resume <thread_id> "Fix: <findings>"`), re-review, and repeat. Save the Opus output to
`output/evidence/orch/<gap>/review.json` so the standard `review_clean` gate applies uniformly.

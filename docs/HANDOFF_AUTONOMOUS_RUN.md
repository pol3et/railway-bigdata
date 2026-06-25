# Handoff — autonomous overnight run readiness

> Written 2026-06-25 by the orchestrator session after a bounded first test run hardened the harness.
> A FRESH session can read this and launch the unattended run (Sessions A+B) with confidence.
> Companions: `docs/OVERNIGHT_READINESS.md` (go/no-go), `docs/ORCHESTRATION.md` (topology),
> `docs/ROADMAP_NEWS_TO_REPORT.md` + `docs/GAP_TASKS.md` (specs).

## TL;DR

The test run found that the orchestration **had never actually worked** (it always ran dry) and that
**every codex call would 400** on an invalid output schema. Both are fixed. The full real cycle was
then proven end-to-end on **GAP-039**, which is now **merged** (PR #28) with main green.

- **3 harness bugs fixed** (DRY always-dry; two invalid output schemas; codex timeout too short).
- **Tiered PR review policy added** (load-bearing PR → Opus subagent; else codex; fixes always codex).
- **GAP-039 merged** (PR #28, squash `dafcbf8`); main = **187 passed, 3 skipped** (~20s).
- **All preconditions GO**; Ollama flash-attention-OFF proven functionally on the Pascal GPU.

## Harness changes made this session

### 1. Showstopper: the run never left dry-run mode
`run_night.sh` set `DRY=0` then passed `${DRY:+--dry-run}` — but `${VAR:+x}` substitutes `x` for any
*non-null* value, and `"0"` is non-null, so `run_wave.sh` **always** got `--dry-run`. The "real" run
no-op'd in 13 s. `run_wave.sh` had the same gotcha in its `${DRY:+[DRY-RUN]}` log label.
**Fix:** `DRY=` (empty) instead of `DRY=0` for the not-dry case in both files — `${DRY:+…}` now
behaves and every `[ "$DRY" = 1 ]` test stays correct (empty ≠ 1).

### 2. Showstopper: every codex call 400'd on the output schema
Strict structured-output now requires `required` to list **every** property. Both
`scripts/orch/schemas/impl_verdict.schema.json` and `review_findings.schema.json` listed only a
subset → `invalid_json_schema` 400, killing every implementer/reviewer instantly.
**Fix:** both schemas now list all properties in `required` (nullable fields stay nullable; arrays
default to `[]`); validated recursively strict-compliant.

### 3. Codex timeouts raised (owner request)
Parallel fan-out absorbs wall-clock, so a long per-agent cap doesn't bottleneck — it only stops
killing a *working* agent (GAP-039 was killed at 40 m having finished, just before committing).
- `codex_impl.sh`: 40 m → **2 h**; `run_wave.sh` auto-resume: 40 m → **2 h**; `codex_review.sh`: 20 m → **1 h**.
- Caps are kept (not unbounded) so a genuinely stuck agent can't hang a sequential wave forever.
- Parallel cap is `ORCH_PAR_CAP` (default **3**, env-overridable). Kept at 3: each AUTO agent runs the
  full suite (CPU/RAM heavy) and this box is RAM-bound; LIVE gaps are force-serial regardless. Bump to
  4 cautiously if desired (`ORCH_PAR_CAP=4 bash scripts/orch/run_night.sh`); higher risks OOM/thrash.

### 4. Tiered PR review (owner policy 2026-06-25)
The reviewer is chosen **per-PR by what the PR changes**, not by a per-gap label:
- **Load-bearing PR** (touches a `LOAD_BEARING_PATHS` core path — data contract / numeric merges /
  LLM extraction+cache / Gold / Spark; matched against the impl verdict's `files_changed` by
  `pr_is_load_bearing` in `run_wave.sh`) → reviewed by an **Opus** `ship-it:ship-reviewer` subagent
  (rubric `scripts/orch/prompts/opus_review.md`). The bash runner runs codex review only as
  **advisory** and parks the gap **`needs_opus_review`** (never auto-merges it). The orchestrator
  dispatches the Opus review and merges on a clean Opus verdict (approve, no P1/P2) + clean impl verdict.
- **Any other PR** → codex review + unattended auto-merge (as before).
- **Fixes are ALWAYS codex** — Opus only reviews; findings go back via `codex exec … resume`.
- New ledger status `needs_opus_review`; `skip_or_run` skips it on resume (orchestrator owns it).

## First test run — GAP-039 (MERGED ✅)

GAP-039 = "wide NewsFeature contract + content-hash cache" (the Session-A unblocker, AUTO/no-GPU).
Driven through the **full real cycle**, which validated every component:
1. `codex_impl.sh GAP-039` — implemented (11 modified + 6 new files; cache, failure accounting, 2 test
   files), full suite green (183 passed) — but hit the (old) 40 m cap before committing → **resume**
   shipped it: PR #28 opened, mergeable.
2. **codex review** (advisory) caught a real **P1**: the cache existed but wasn't wired into the
   production path (`pipeline.py`/`silver/run.py` used `NoOpCache`), plus P2 (GDELT passthrough
   unreachable) + P3 (`gkg_tone=0` dropped by truthiness). The gate correctly **refused to merge**.
3. **fix-resume** (codex — fixes are always codex) wired the cache into production, fixed P2/P3, and
   added regression tests (suite 183 → **187 passed, 3 skipped**); PR #28 updated, mergeable.
4. Opus review was **waived by owner** for this test wrap-up; **PR #28 squash-merged** (`dafcbf8`).
   Post-merge contract suite on main: **187 passed, 3 skipped (~20 s)** — green.

Net: implement → timeout-resume → codex review → fix-resume → merge → contract are ALL proven on real
work. GAP-039 (the unblocker the rest of Session A depends on) is done.

## Preconditions (verified 2026-06-25)

| Check | Result |
|---|---|
| `gh auth` | pol3et active, repo+workflow (write). cul8err also present. |
| MinIO | `railway-minio` up (9000-9001). |
| Ollama | HTTP 200; `qwen3:4b` present. **FA-off proven**: a live `format=json` chat returned valid JSON, `done_reason:stop`, **no CUDA crash** (FA-on crashes on Pascal). `OLLAMA_FLASH_ATTENTION=0` persisted; `lib_run.sh` exports FA=0 + `NUM_CTX=4096`. |
| JDK 21 | present; `lib_run.sh` self-sets `JAVA_HOME` (empty at shell is expected). |
| codex | 0.142.0. Full suite is ~20 s — fast. |
| git | on `main` at `dafcbf8` after the GAP-039 merge. **Other sessions push to `main` concurrently** (origin moved twice this session). |

## Current state

- **Ledger** `output/evidence/orch/run_state.json`: `{ "GAP-039": "merged" (PR 28) }`. All other gaps
  absent → the run will process them. (Resets are safe; only `merged`/`needs_opus_review`/MANUAL/CLAUDE
  are skipped on resume.)
- **Open PRs:** none. **Worktrees:** clean (wt-gap-039 removed).
- **main HEAD:** `dafcbf8` (GAP-039 merged), suite green.

## Resume — launching the autonomous run in a fresh session

1. `gh auth switch --user pol3et` (other sessions flip this to cul8err).
2. `git -C <repo> fetch origin main && git -C <repo> merge --ff-only origin/main`.
3. Re-prove Ollama FA-off with the `format=json` smoke (Recipe A) — a reboot can lose it.
4. `bash scripts/orch/run_night.sh --dry-run` → expect `[DRY-RUN]` + `DRY impl …` (sanity).
5. **Launch:** `bash scripts/orch/run_night.sh` (orchestrator session in an auto-approve/bypass mode).
   - Resumable via the ledger; GAP-039 (merged) is skipped → it resumes at GAP-050.
   - LIVE gaps (GAP-033 Ollama, GAP-036 sidecar) auto-serialized (single-box rule).
   - **Load-bearing PRs park `needs_opus_review`** — they do NOT auto-merge.
6. **Orchestrator duties during/after the run** (not fire-and-forget for load-bearing work):
   - For every `needs_opus_review` gap: dispatch an **Opus** `ship-it:ship-reviewer` (model: opus,
     rubric `scripts/orch/prompts/opus_review.md`); if approve + no P1/P2 + clean verdict → merge; else
     feed findings to **codex** (`codex exec … resume <thread_id>`), re-review, repeat.
   - **WAVE 6a is a load-bearing dependency chain** (GAP-050 → GAP-033). Shepherd it gap-by-gap:
     impl → Opus review → (codex fix if needed) → merge → next. Don't expect 6a to self-complete.
   - **GAP-043 (CLAUDE)** — after GAP-033 merges: Opus subagent DESIGNS the golden set + eval harness +
     rubric (GAP_TASKS GAP-043 + `docs/SPEC_NEWS_PREPROCESSING.md` §6: TUNE/TEST split, collapsed
     taxonomy, CIs); **Sonnet** subagents LABEL a stratified sample of the real extracted articles
     (**never qwen3:4b**); then `codex_impl.sh GAP-043` wires+tests the harness vs the silver labels;
     gate on **non-regression**. Run it as a clean post-run step.
7. Morning: summarize the ledger; `merged`=done, `needs_opus_review`=Opus-review-then-merge,
   `parked_*`=open PR, `manual_skip`=GAP-037/038 + Session C; append `docs/WAVE_LOG.md`;
   `gh auth switch cul8err`.

## Simplifications adopted (orchestration was over-engineered)

- **Dropped the mid-run GAP-033 watcher** (extra background process + concurrency hazard). GAP-043 is
  a clean post-run step, not a mid-run trigger.
- **Reviewer routing is per-PR (content-based), not a per-gap config map** — simpler and matches "is
  this PR load-bearing".

## Risks / watch-items

- **Concurrent sessions push to `main`** (origin moved `0a84012` → `7761e2e` → `dafcbf8` this session,
  incl. a commit that gitignored a stray root `silver/` cache). Sync before launching; keep gh on
  **pol3et** (only write account).
- **Single-box live lane:** never two model passes at once; the runner serializes LIVE gaps.
- **Transient parse glitch (non-issue):** one sandbox-disabled background invocation once emitted a
  spurious `run_wave.sh: line 116: syntax error` that does NOT reproduce (`bash -n` clean). Watch only.
- **Scope:** Sessions A+B only. Session C (GAP-046/048/049; GAP-047) is NOT in `NIGHT_WAVES`.
  GAP-037/038 are MANUAL (skipped+logged).

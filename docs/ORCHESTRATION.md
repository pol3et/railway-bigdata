# Wave Orchestration — Claude orchestrator + Codex implementers

How we drive the `docs/TASKS.md` execution waves to **END OF FAST TRACK**: a single
**Claude Code** session orchestrates; **Codex** (`codex exec`) implements each gap and
opens a mergeable PR; review is independent; the orchestrator merges, audits the wave
**contract**, then advances.

Feasibility was verified live (Codex 0.142, ChatGPT auth): `codex exec --json` launches
headless, emits `thread.started{thread_id}` → `turn.completed`, captures the final message
via `--output-last-message`, and resumes via `codex exec resume <thread_id>`.

## Roles (division of labor — locked 2026-06-25)

**Claude does research + spec; Codex reviews/improves the spec + implements + tests.**

- **Claude = orchestrator (thin).** Holds the wave plan + contracts + decisions only. Never
  implements; never reads full diffs/test logs into its own context (that's what keeps one
  long session alive under auto-compaction).
- **Claude research+spec subagent**, one per gap, dispatched by the orchestrator (Agent/Task
  tool) **before** Codex. It runs **`/research-orchestrator`** (+ task-relevant skills, e.g.
  `prompt-master`/`senior-prompt-engineer` for LLM gaps, `senior-data-engineer` for Spark)
  against the live code + the `docs/GAP_TASKS.md` spec, freshens/sharpens that spec with
  current research (cited URLs), and writes the **finalized per-gap spec** to
  `output/evidence/orch/<gap>/spec.md` (+ the research record under
  `.planning/coursework/research/bigdata/<gap-slug>.md`). This is the only research/spec author.
- **Codex `exec` = spec-improver + implementer + tester**, one per gap, **full access / yolo**
  (`--dangerously-bypass-approvals-and-sandbox`), in its **own git worktree**. Driven by its
  `$ship-it` workflow with **no Linear**. It **first reviews and improves the handed spec**
  (sanity-checks it against the live code; refines via `$ship-it` + research MCPs only where the
  spec is wrong/thin), then **self-reviews/approves** its plan and **implements + writes & runs
  tests** against it, auto-approving its own steps (yolo). Returns a structured verdict
  (`schemas/impl_verdict.schema.json`).
- **Reviewers**: Codex (`$ship-it` review / `codex_review.sh`, independent read-only pass) +
  a `ship-it:ship-reviewer` Claude subagent for hard PRs + an orchestrator eyeball.

## Decisions (locked)
- **Context:** one long orchestrator session + transparent auto-compaction. The orchestrator
  cannot self-`/compact` (no such tool); it stays small by **delegating** all heavy work to
  Codex processes / subagents and reading only one-line summaries back.
- **PR identity:** Codex pushes + opens PRs as **`pol3et`** (the only account with write).
  `scripts/orch/lib.sh:ensure_pol3et` switches gh before each implementer; restore `cul8err`
  at the end of the session.

## Environment gotchas (baked into the scripts)
- `--dangerously-bypass-approvals-and-sandbox` removes sandbox + approvals **and** the network
  block, so `git push` / `gh pr create` work. (Plain `-s workspace-write` disables network.)
- **Exit code ≠ success**: `codex exec` can exit 0 with a failed inner command. Outcome is
  judged by parsing JSONL (`turn.completed`, no `turn.failed`/`error`) + the verdict JSON.
- gh/git identity is inherited from the env (hence `ensure_pol3et`); `AGENTS.md` is
  auto-discovered by Codex, so our Hard Rules apply automatically.
- One shared MinIO. Integration tests use `tmp_path`/fixtures (repo rule), so parallel
  implementers don't collide; the live MinIO smoke is the only shared-state test — serialize
  if two gaps touch it.

## Per-wave loop
For each wave in `docs/TASKS.md` (Wave 1 → 2 → 3 = fast track):

1. **Prep**: `docker compose up -d`; `gh auth switch pol3et`; `git -C . fetch origin main`.
2. **Research + spec (Claude), then fan out (Codex)** — tasks in the wave run in parallel, each its own worktree/branch/PR:
   - **2a. Claude research+spec subagent per gap** (Agent/Task): runs `/research-orchestrator` (+ task skills like `prompt-master` for LLM gaps), refreshes the `docs/GAP_TASKS.md` spec against the live code, and **writes `output/evidence/orch/<gap>/spec.md`** (the finalized spec Codex will use) + the research record. Dispatch these in parallel; read only the one-line "spec ready" back.
   - **2b. Codex implementers** (use the Claude-written spec.md if present; else `gap_spec` falls back to GAP_TASKS):
   ```bash
   scripts/orch/codex_impl.sh GAP-012      # ‖
   scripts/orch/codex_impl.sh GAP-017      # ‖   (launch in background; watch with Monitor)
   ```
   Each Codex first reviews/improves the spec, then implements + tests (yolo, self-approve), and writes `output/evidence/orch/<gap>/{run.jsonl,verdict.json,thread_id.txt}`.
3. **Collect**: read each `verdict.json`. If `blocked` or tests failing, resume the SAME
   Codex session to fix:
   ```bash
   WT=../wt-gap-012; TID=$(cat output/evidence/orch/gap-012/thread_id.txt)
   codex exec --dangerously-bypass-approvals-and-sandbox -C "$WT" resume "$TID" \
     "Blocker: <x>. Resolve it, get the suite green, and finish the mergeable PR."
   ```
4. **Review** each PR (independent):
   ```bash
   scripts/orch/codex_review.sh GAP-012     # structured findings -> review.json
   ```
   For a gnarly PR, also dispatch a `ship-it:ship-reviewer` Claude subagent. Feed
   `request_changes` findings back via `codex exec ... resume <TID> "Fix: <findings>"`.
   Orchestrator eyeballs the final diff (`gh pr diff <n>`).
5. **Merge in dependency order** (data-spine first): `gh pr merge <n> --squash --delete-branch`,
   then on `main` re-run `python -m pytest -q`. Resolve conflicts before the next merge.
6. **Contract audit**: run the wave's Contract (A/B/C in `docs/TASKS.md`) verification
   commands; record evidence under `output/evidence/orch/contract-<wave>/`. Any unmet item →
   dispatch a Codex fix (`codex_impl.sh` on the leftover, or `resume`).
7. **Advance**: append a `docs/WAVE_LOG.md` entry (merged PRs, contract status, evidence) +
   sync `docs/index.html`/`TASKS.md` (dashboard Hard Rule). Continue to the next wave. Stop at
   🏁 **END OF FAST TRACK** (after Wave 3 / report kickoff).
8. **Cleanup**: `git worktree remove ../wt-<gap>` for merged gaps; `gh auth switch cul8err`.

## Files
- `scripts/orch/lib.sh` — env preconditions, JSONL outcome parsing, gap-spec extraction.
- `scripts/orch/codex_impl.sh <GAP-ID>` — worktree + full-access Codex implementer + verdict.
- `scripts/orch/codex_review.sh <GAP-ID>` — read-only structured Codex review of the branch.
- `scripts/orch/prompts/impl.tmpl.md` — implementer prompt (embeds the gap spec; `$ship-it`).
- `scripts/orch/schemas/*.json` — implementer verdict + review-findings output schemas.
- `scripts/orch/run_night.sh [--dry-run]` — **UNATTENDED driver**: runs the waves in order, auto-merges
  clean PRs, stops on a contract fail; resumable via the run-state ledger. See `docs/OVERNIGHT_READINESS.md`.
- `scripts/orch/run_wave.sh <WAVE> <seq|par>` — one wave: fan out implementers (LIVE serialized), review,
  auto-merge-on-approve, contract audit.
- `scripts/orch/night.config.sh` — gap classification (AUTO/LIVE/MANUAL) + wave lists + contract commands.
- `scripts/orch/lib_run.sh` — verdict/review merge gates, run-state ledger, main-checkout sync.

## Unattended overnight run (single-box rules)
- The manual per-wave **CHECKPOINT** is **superseded** by `run_night.sh` for AUTO/LIVE gaps: it
  auto-merges a PR ONLY when `mergeable` + suite green + an independent review `approve`s with **no P1/P2**;
  otherwise the PR is left OPEN and the gap is **parked** for morning. **MANUAL** gaps (golden-set labelling,
  hypothesis formation, final report, Session C Spark finale) are skipped + logged, never auto-produced.
- **Single-box live lane:** models run SEQUENTIALLY (6 GB GPU). The runner serializes LIVE gaps
  (Ollama / encoder sidecar / live-MinIO write) — never two at once — while AUTO (mock/fixture) gaps fan out.
- **Survivable state:** every step writes `output/evidence/orch/run_state.json`; re-running resumes
  (merged gaps skipped) so orchestrator context-compaction or a crash never loses progress.
- Preconditions + Ollama/encoder-sidecar recipes + go/no-go: `docs/OVERNIGHT_READINESS.md`.

## Guardrails
- Implementers are bounded to one gap (the prompt forbids scope-widening).
- Any external research an implementer needs goes through the **`/research-orchestrator`** skill
  and its MCP providers (Context7/Ref/Tavily/Exa/Firecrawl), with cited URLs recorded under
  `.planning/coursework/research/bigdata/` — no ad-hoc browsing or memory-only claims.
- Nothing merges to `main` without: green suite on the branch, an independent review pass with
  no open P1/P2, and the orchestrator's eyeball.
- The wave does not advance until its **contract** verification passes on `main`.

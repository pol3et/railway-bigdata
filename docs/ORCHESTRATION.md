# Wave Orchestration — Claude orchestrator + Codex implementers

How we drive the `docs/TASKS.md` execution waves to **END OF FAST TRACK**: a single
**Claude Code** session orchestrates; **Codex** (`codex exec`) implements each gap and
opens a mergeable PR; review is independent; the orchestrator merges, audits the wave
**contract**, then advances.

Feasibility was verified live (Codex 0.142, ChatGPT auth): `codex exec --json` launches
headless, emits `thread.started{thread_id}` → `turn.completed`, captures the final message
via `--output-last-message`, and resumes via `codex exec resume <thread_id>`.

## Roles
- **Claude = orchestrator (thin).** Holds the wave plan + contracts + decisions only. Never
  implements; never reads full diffs/test logs into its own context (that's what keeps one
  long session alive under auto-compaction).
- **Codex `exec` = implementer**, one per gap, **full access**
  (`--dangerously-bypass-approvals-and-sandbox`), in its **own git worktree**. Driven by its
  `$ship-it` workflow with **no Linear** — all context is the repo's code + docs. It first
  writes **one plan, self-reviews/approves it**, then implements against it. Returns a
  structured verdict (`schemas/impl_verdict.schema.json`).
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
2. **Fan out** (tasks in the wave run in parallel — each its own worktree/branch/PR):
   ```bash
   scripts/orch/codex_impl.sh GAP-012      # ‖
   scripts/orch/codex_impl.sh GAP-017      # ‖   (launch in background; watch with Monitor)
   ```
   Each writes `output/evidence/orch/<gap>/{run.jsonl,verdict.json,thread_id.txt}`.
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

## Guardrails
- Implementers are bounded to one gap (the prompt forbids scope-widening).
- Any external research an implementer needs goes through the **`/research-orchestrator`** skill
  and its MCP providers (Context7/Ref/Tavily/Exa/Firecrawl), with cited URLs recorded under
  `.planning/coursework/research/bigdata/` — no ad-hoc browsing or memory-only claims.
- Nothing merges to `main` without: green suite on the branch, an independent review pass with
  no open P1/P2, and the orchestrator's eyeball.
- The wave does not advance until its **contract** verification passes on `main`.

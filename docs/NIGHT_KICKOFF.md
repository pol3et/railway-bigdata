# Night session kickoff

**Goal:** finish Sessions A+B and keep going until every in-scope gap is `merged`. GAP-039 is already
merged. Out of scope (skip): Session C (GAP-046/047/048/049) and GAP-037/038 (MANUAL).
Track state in `output/evidence/orch/run_state.json`. Be in an auto-approve/bypass mode.

## 0. Start (preconditions)
```bash
gh auth switch --user pol3et
git fetch origin main && git merge --ff-only origin/main
# Ollama must answer JSON with NO CUDA crash (proves flash-attention is OFF on the Pascal GPU):
curl -s -X POST http://localhost:11434/api/chat -H "Content-Type: application/json" \
  -d '{"model":"qwen3:4b","stream":false,"format":"json","think":false,"options":{"temperature":0,"num_ctx":4096},"messages":[{"role":"user","content":"Reply with JSON {\"ok\":true} only."}]}'
```
If the curl errors/crashes → flash-attention is on; stop and fix before any live gap.

## 1. WAVE 6a — load-bearing chain, drive ONE AT A TIME (GAP-050 → GAP-033)
These are load-bearing AND dependency-ordered, so don't fire-and-forget. For each, in order:
```bash
bash scripts/orch/codex_impl.sh GAP-050        # then GAP-033 (LIVE Ollama — nothing else may use the GPU)
```
Then **Opus-review → merge** (see §3). Merge GAP-050 before GAP-033 runs (033 builds on 050).

## 2. WAVES 6b + B — fan out
```bash
bash scripts/orch/run_night.sh      # skips already-merged gaps; auto-merges simple (codex) PRs;
                                    # parks load-bearing PRs as `needs_opus_review`; serializes LIVE gaps
```

## 3. Review + merge each parked PR (the orchestrator's standing job)
- **`needs_opus_review`** (load-bearing): dispatch an **Opus** `ship-it:ship-reviewer` (model: opus,
  rubric `scripts/orch/prompts/opus_review.md`; feed it `gh pr diff <PR>`, the spec, and
  `output/evidence/orch/<gap>/verdict.json`). If `approve` + no P1/P2 →
  `gh pr merge <PR> --squash --delete-branch && git merge --ff-only origin/main`.
- **`parked_*`**: read `output/evidence/orch/<gap>/{verdict,review}.json`.
- To fix any findings: **codex only** — `codex exec --dangerously-bypass-approvals-and-sandbox
  -C ../wt-<gap> resume <thread_id> "Fix: <findings>"` → re-review → merge. (Opus reviews; never edits.)
- Re-run `bash scripts/orch/run_night.sh` after merges to advance dependents. **Loop §2–§3 until done.**

## 4. GAP-043 (only after GAP-033 is merged)
Opus subagent DESIGNS the golden set + eval harness + rubric (`docs/GAP_TASKS.md` GAP-043 +
`docs/SPEC_NEWS_PREPROCESSING.md` §6: TUNE/TEST split, collapsed taxonomy, CIs). **Sonnet** subagents
LABEL a stratified sample of the real extracted articles — **never qwen3:4b** (the evaluated model).
Then `bash scripts/orch/codex_impl.sh GAP-043` wires+tests vs the silver labels → Opus review → merge.
Gate on **non-regression** (silver labels → numbers indicative).

## 5. Done
All in-scope gaps `merged` (037/038 = `manual_skip`). Append one line to `docs/WAVE_LOG.md`,
`gh auth switch cul8err`, and report any gap left `parked_*` for the owner.

---
Why/detail (only if stuck): `docs/HANDOFF_AUTONOMOUS_RUN.md`. Keep gh on **pol3et** (only write
account; other sessions flip it). Never run two model passes at once (single 6 GB GPU).

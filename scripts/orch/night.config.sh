#!/usr/bin/env bash
# Configuration for the unattended overnight run. Sourced by run_night.sh.
#
# Gap classes:
#   AUTO   = builds + tests with mocked models / fixtures (tmp_path). Safe to run
#            unattended and auto-merge on a clean verdict + approving review.
#   LIVE   = needs an EXCLUSIVE single-box resource (Ollama GPU pass, or a live
#            MinIO write). MUST run serialized — never two LIVE gaps at once.
#   MANUAL = needs human judgement (hypothesis selection, report narrative). The runner SKIPS
#            these and logs them; it never auto-produces this work (quality gate).
#   CLAUDE = handled by the orchestrator CLAUDE session via subagents (e.g. Opus design + Sonnet
#            labelling), NOT by a Codex implementer. The bash wrapper SKIPS it and logs a pointer;
#            the orchestrator session runs it separately (after its dependency merges).
declare -gA GAP_CLASS=(
  # --- Session A · WAVE 6a (sequential: dependency chain) ---
  [GAP-039]=AUTO     # wide NewsFeature contract + content-hash cache (the unblocker)
  [GAP-050]=AUTO     # LLM pipeline engineering (prompt/batch/cache/retry/metrics; LLM mocked in tests)
  [GAP-033]=LIVE     # first REAL Ollama run — needs the GPU + a pulled model
  # --- Session A · WAVE 6b (parallel; depend on 039 merged) ---
  [GAP-035]=AUTO     # fastText language-id (CPU, tiny)
  [GAP-034]=AUTO     # XLM-R sentiment encoder (CPU-first; tests mock/fixture)
  [GAP-031]=AUTO     # GDELT DOC-field recovery + wire passthrough (no model)
  [GAP-040]=AUTO     # widen Gold news aggregation (+GAP-016/022/026)
  [GAP-044]=AUTO     # per-source parser-correctness audit (fixtures)
  [GAP-043]=CLAUDE   # eval harness; golden set DESIGNED by an Opus subagent + LABELLED by Sonnet subagents (orchestrator dispatches these — NOT the bash Codex loop, NOT qwen3:4b); needs GAP-033 real rows
  # --- Session B (parallel; stats-side + encoders) ---
  [GAP-045]=AUTO     # +2 World Bank macro indicators (IS.VEH.PCAR.P3, PA.NUS.PPP)
  [GAP-041]=AUTO     # UIC PDF widen-to-all-countries + stage unmapped rows
  [GAP-042]=AUTO     # Statistik Austria ODS reader
  [GAP-036]=LIVE     # embeddings + cross-lingual dedup (GPU sidecar)
  [GAP-037]=MANUAL   # Spark clustering — non-deterministic; separate artifact (Session C)
  [GAP-038]=MANUAL   # NER — deferred (gazetteer-first); lowest payoff
  # --- Session C · the finale (DEFERRED to a separate session by owner) ---
  [GAP-046]=MANUAL   # Spark EDA harness (Session C)
  [GAP-047]=AUTO     # analysis_artifacts inbox + verifier (infra is automatable)
  [GAP-048]=MANUAL   # form hypotheses FROM EDA — human judgement
  [GAP-049]=MANUAL   # final report narrative — human judgement
)

# Reviewer is chosen PER-PR by what the PR changes, NOT by a per-gap label (owner policy 2026-06-25):
#   * A PR is LOAD-BEARING if it touches any core path below (data contract / numeric merges / LLM
#     extraction+cache / Gold / Spark analysis). Load-bearing PRs are reviewed by an OPUS subagent
#     (orchestrator dispatches `ship-it:ship-reviewer`, rubric scripts/orch/prompts/opus_review.md);
#     the bash runner runs codex review only as ADVISORY and parks the gap `needs_opus_review`.
#   * Any other PR is reviewed by codex and auto-merged on a clean verdict + approving review.
#   * FIXES ARE ALWAYS CODEX (Opus only reviews; findings go back via `codex exec … resume`).
# Evaluated against the impl verdict's files_changed (see pr_is_load_bearing in run_wave.sh).
LOAD_BEARING_PATHS='src/railway_lakehouse/(pipeline\.py|silver/(persist|schema|run)\.py|silver/news/(extract|cache)\.py|silver/stats/.*merge.*\.py|gold/|spark_jobs/)'

# Ordered gap lists per wave. 6a is a dependency chain (run sequential); the
# others fan out (run parallel, but LIVE gaps within them are still serialized).
WAVE_6A="GAP-039 GAP-050 GAP-033"
WAVE_6B="GAP-031 GAP-035 GAP-034 GAP-040 GAP-044 GAP-043"
WAVE_B="GAP-045 GAP-041 GAP-042 GAP-036 GAP-037 GAP-038"

# What the overnight run attempts, in order. Session C is intentionally absent
# (owner: save the Spark finale for a separate, supervised session).
NIGHT_WAVES="6a:seq 6b:par B:par"

# Contract audit command per wave (run on the synced main after the wave merges).
# Richer contract checklists live in docs/TASKS.md (Contracts D/E) and are verified
# by a human in the morning; here we gate on the full suite staying green.
declare -gA CONTRACT_CMD=(
  [6a]="python -m pytest -q"
  [6b]="python -m pytest -q"
  [B]="python -m pytest -q"
)

#!/usr/bin/env bash
# Independent Codex review of a gap's implementation branch (read-only, structured).
#   scripts/orch/codex_review.sh <GAP-ID> [base=main]
# Produces output/evidence/orch/<gap>/{review.json,review.jsonl}
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib.sh"

GAP_ID="${1:?usage: codex_review.sh <GAP-ID> [base]}"
BASE="${2:-main}"
GAP_LC="$(printf '%s' "$GAP_ID" | tr 'A-Z' 'a-z')"
WT="$REPO_ROOT/../wt-$GAP_LC"
OUT="$EVID/$GAP_LC"; mkdir -p "$OUT"
[ -d "$WT" ] || { orch_log "no worktree $WT — run codex_impl.sh $GAP_ID first"; exit 1; }

PROMPT="Review the changes on this branch against $BASE. Run \`git diff $BASE...HEAD\` and read the changed files. Judge: (1) correctness and edge cases; (2) whether the $GAP_ID Definition-of-Done / contract in docs/GAP_TASKS.md is actually met; (3) tests exist, are deterministic, and meaningfully cover the change (unit + integration; live only if the DoD needs it); (4) AGENTS.md Hard Rules — raw Bronze immutable, numeric merges deterministic (no LLM-rewritten numbers), no fabricated data, outputs under output/, dashboard kept in sync if pipeline state changed. Be a skeptic. Output ONLY the JSON object per the schema: verdict approve|request_changes, prioritized findings (P1-P4) with file:line and a concrete fix, and which contract items you verified."

orch_log "Codex review of $GAP_ID vs $BASE (read-only)"
# Generous cap (1h): parallel agents overlap, so a long timeout doesn't bottleneck wall-clock;
# it only stops a genuinely stuck agent. Raised from 1200 after a working agent was killed mid-run.
timeout 3600 codex exec --json -s read-only \
  -C "$WT" \
  --output-schema "$HERE/schemas/review_findings.schema.json" \
  -o "$OUT/review.json" \
  "$PROMPT" > "$OUT/review.jsonl" 2> "$OUT/review.log"
codex_ok "$OUT/review.jsonl" && orch_log "review turn.completed" || orch_log "review turn FAILED — see $OUT/review.jsonl"
echo "----- review -----"; cat "$OUT/review.json" 2>/dev/null || orch_log "no review.json captured"

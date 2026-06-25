#!/usr/bin/env bash
# Launch a Codex implementer for one gap in an isolated git worktree, full access.
#   scripts/orch/codex_impl.sh <GAP-ID> [base=main]
# Produces output/evidence/orch/<gap>/{prompt.md,run.jsonl,run.log,verdict.json,thread_id.txt}
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib.sh"

GAP_ID="${1:?usage: codex_impl.sh <GAP-ID> [base]}"
BASE="${2:-main}"
GAP_LC="$(printf '%s' "$GAP_ID" | tr 'A-Z' 'a-z')"
WT="$REPO_ROOT/../wt-$GAP_LC"
BRANCH="impl/$GAP_LC"
OUT="$EVID/$GAP_LC"; mkdir -p "$OUT"

ensure_pol3et || exit 1
ensure_minio  || exit 1

git -C "$REPO_ROOT" fetch origin "$BASE" >/dev/null 2>&1 || true
if [ -d "$WT" ]; then
  orch_log "worktree $WT exists; reusing"
else
  git -C "$REPO_ROOT" worktree add -b "$BRANCH" "$WT" "origin/$BASE" 2>"$OUT/wt.log" \
    || git -C "$REPO_ROOT" worktree add "$WT" "$BRANCH" 2>>"$OUT/wt.log" \
    || { orch_log "worktree add failed (see $OUT/wt.log)"; exit 1; }
fi

# Prefer a Claude research+spec subagent's finalized spec if it pre-wrote one (new division of
# labor, docs/ORCHESTRATION.md); else fall back to extracting the static GAP_TASKS spec.
if [ -s "$OUT/spec.md" ]; then
  orch_log "using existing Claude-authored spec $OUT/spec.md"
else
  gap_spec "$GAP_ID" > "$OUT/spec.md"
fi
python - "$HERE/prompts/impl.tmpl.md" "$OUT/spec.md" "$GAP_ID" "$GAP_LC" "$OUT/prompt.md" <<'PY'
import sys
tmpl=open(sys.argv[1],encoding="utf-8").read()
spec=open(sys.argv[2],encoding="utf-8").read()
gid,glc,outp=sys.argv[3],sys.argv[4],sys.argv[5]
open(outp,"w",encoding="utf-8").write(
    tmpl.replace("{{GAP_ID}}",gid).replace("{{GAP_ID_LC}}",glc).replace("{{GAP_SPEC}}",spec))
PY

orch_log "launching Codex implementer for $GAP_ID (branch $BRANCH, worktree $WT)"
# Generous cap (2h): an implementer does real work — edit + tests + full suite + commit + push + PR.
# Parallel fan-out absorbs the wall-clock cost; this only kills a genuinely stuck agent. Raised from
# 2400 after a green GAP-039 agent was killed at 40m mid-ship (it had finished, just hadn't committed).
timeout 7200 codex exec --json \
  --dangerously-bypass-approvals-and-sandbox \
  -C "$WT" \
  --output-schema "$HERE/schemas/impl_verdict.schema.json" \
  -o "$OUT/verdict.json" \
  - < "$OUT/prompt.md" > "$OUT/run.jsonl" 2> "$OUT/run.log"
RC=$?

TID="$(codex_thread_id "$OUT/run.jsonl")"; printf '%s\n' "$TID" > "$OUT/thread_id.txt"
[ "$RC" -eq 124 ] && orch_log "codex TIMED OUT (40m)"
[ "$RC" -ne 0 ] && [ "$RC" -ne 124 ] && orch_log "codex infra exit $RC (see $OUT/run.log)"
if codex_ok "$OUT/run.jsonl"; then orch_log "$GAP_ID: turn.completed"; else orch_log "$GAP_ID: turn FAILED/incomplete — inspect $OUT/run.jsonl"; fi
orch_log "thread_id=$TID  verdict=$OUT/verdict.json"
echo "----- verdict -----"; cat "$OUT/verdict.json" 2>/dev/null || orch_log "no verdict.json captured"

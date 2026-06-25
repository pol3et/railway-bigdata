#!/usr/bin/env bash
# Run ONE wave unattended.
#   scripts/orch/run_wave.sh <WAVE> <seq|par> [--dry-run]
# WAVE is a key whose gap list is WAVE_<UPPER> in night.config.sh (e.g. 6a -> WAVE_6A).
#
# seq : implement+review+merge each gap one at a time (dependency chains, e.g. 6a).
# par : implement AUTO gaps concurrently (capped) + LIVE gaps serialized; then
#       review + merge each serially.
#
# A gap is auto-merged ONLY if: verdict mergeable + not blocked + suite green AND an
# independent review approves with no P1/P2. Otherwise the PR is left OPEN and the gap
# is PARKED in the run-state ledger for morning review. MANUAL gaps are skipped + logged.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib.sh"
source "$HERE/lib_run.sh"
source "$HERE/night.config.sh"

WAVE="${1:?usage: run_wave.sh <WAVE> <seq|par> [--dry-run]}"
MODE="${2:?usage: run_wave.sh <WAVE> <seq|par> [--dry-run]}"
# DRY must be EMPTY (not "0") when not dry-running — it feeds ${DRY:+[DRY-RUN]} (line 27),
# and ${VAR:+x} substitutes x for any set & non-null VAR, so "0" would force dry labelling.
DRY=; [ "${3:-}" = "--dry-run" ] && DRY=1
CAP="${ORCH_PAR_CAP:-3}"   # max concurrent AUTO implementers on this box

RUNSTATE="$EVID/run_state.json"; runstate_init
eval "GAPS=\${WAVE_$(printf '%s' "$WAVE" | tr 'a-z' 'A-Z'):-}"
[ -n "${GAPS:-}" ] || { orch_log "no gap list WAVE_${WAVE^^} in night.config.sh"; exit 2; }
orch_log "=== WAVE $WAVE ($MODE) : $GAPS ${DRY:+[DRY-RUN]}"

gap_class() { printf '%s' "${GAP_CLASS[$1]:-AUTO}"; }
glc_of()    { printf '%s' "$1" | tr 'A-Z' 'a-z'; }

# Per-PR reviewer routing (owner policy): a PR is LOAD-BEARING -> reviewed by an Opus subagent
# (orchestrator), NEVER bash auto-merged, if its impl-verdict files_changed touch a core
# LOAD_BEARING_PATHS path. Anything else is codex-reviewed + auto-merged. Fixes are always codex.
# Default to load-bearing when the verdict is missing/unparseable (safer: don't auto-merge unknowns).
pr_is_load_bearing() {  # <gap> -> exit 0 if load-bearing
  python - "$EVID/$(glc_of "$1")/verdict.json" "${LOAD_BEARING_PATHS:-}" <<'PY'
import json,sys,re
try: v=json.load(open(sys.argv[1],encoding="utf-8"))
except Exception: sys.exit(0)            # unknown verdict -> treat as load-bearing
pat=sys.argv[2]
if not pat: sys.exit(1)                   # no pattern configured -> not load-bearing
files=[(f or "").replace("\\","/") for f in (v.get("files_changed") or [])]
rx=re.compile(pat)
sys.exit(0 if any(rx.search(f) for f in files) else 1)
PY
}

impl_one() {  # <gap> : run implementer, one auto-resume if not clean
  local gap="$1" glc out cls; glc="$(glc_of "$gap")"; out="$EVID/$glc"
  if [ "$DRY" = 1 ]; then orch_log "DRY impl $gap"; return 0; fi
  "$HERE/codex_impl.sh" "$gap" >/dev/null 2>&1 || true
  if ! verdict_clean "$out/verdict.json"; then
    local tid blk; tid="$(cat "$out/thread_id.txt" 2>/dev/null)"; blk="$(blocker_of "$out/verdict.json")"
    if [ -n "$tid" ]; then
      orch_log "$gap: not clean (blocker: ${blk:-tests}); ONE resume"
      timeout 7200 codex exec --json --dangerously-bypass-approvals-and-sandbox \
        -C "$REPO_ROOT/../wt-$glc" --output-schema "$HERE/schemas/impl_verdict.schema.json" \
        -o "$out/verdict.json" resume "$tid" \
        "Blocker: ${blk:-suite not green}. Resolve it, make 'python -m pytest -q' green, finish a mergeable PR to main. Final message MUST be ONLY the verdict JSON per the schema." \
        > "$out/resume.jsonl" 2> "$out/resume.log" || true
    fi
  fi
}

review_merge_one() {  # <gap> : review, then auto-merge or park
  local gap="$1" glc out pr; glc="$(glc_of "$gap")"; out="$EVID/$glc"
  if [ "$DRY" = 1 ]; then orch_log "DRY review+merge $gap"; runstate_set "$gap" "dry"; return 0; fi
  if ! verdict_clean "$out/verdict.json"; then
    orch_log "$gap: PARKED (verdict not clean: $(blocker_of "$out/verdict.json"))"
    runstate_set "$gap" "parked_impl" "$(pr_number_of "$out/verdict.json")" "verdict not clean"; return 1
  fi
  pr="$(pr_number_of "$out/verdict.json")"
  "$HERE/codex_review.sh" "$gap" >/dev/null 2>&1 || true   # codex structured findings (advisory if load-bearing)
  if pr_is_load_bearing "$gap"; then
    orch_log "$gap: PR #$pr is LOAD-BEARING (core paths) — NOT auto-merging; awaiting orchestrator Opus review."
    runstate_set "$gap" "needs_opus_review" "$pr" "load-bearing PR: orchestrator Opus ship-reviewer required (codex review.json is advisory)"; return 1
  fi
  if ! review_clean "$out/review.json"; then
    orch_log "$gap: PARKED (codex review requested changes / P1-P2)"
    runstate_set "$gap" "parked_review" "$pr" "review not clean"; return 1
  fi
  ensure_pol3et >/dev/null 2>&1 || true   # gh active account can flip back to cul8err mid-run -> 403 on merge
  orch_log "$gap: clean verdict + approving review -> merging PR #$pr"
  if gh pr merge "$pr" --squash --delete-branch >/dev/null 2>"$out/merge.log"; then
    sync_main
    if main_suite_green; then
      orch_log "$gap: MERGED (PR #$pr); main suite green"
      runstate_set "$gap" "merged" "$pr"; git -C "$REPO_ROOT" worktree remove --force "$REPO_ROOT/../wt-$glc" 2>/dev/null || true; return 0
    else
      orch_log "$gap: ALARM — merged PR #$pr but main suite RED (see $EVID/main_pytest.log)"
      runstate_set "$gap" "merged_suite_red" "$pr" "post-merge pytest failed"; return 1
    fi
  else
    orch_log "$gap: merge FAILED (conflict?) — PARKED (see $out/merge.log)"
    runstate_set "$gap" "parked_merge" "$pr" "gh pr merge failed"; return 1
  fi
}

skip_or_run() {  # returns 1 if the gap should be skipped (already merged / manual)
  local gap="$1" st cls; st="$(runstate_get "$gap")"; cls="$(gap_class "$gap")"
  if [ "$st" = "merged" ]; then orch_log "$gap: already merged (resume) — skip"; return 1; fi
  if [ "$st" = "needs_opus_review" ]; then orch_log "$gap: awaiting orchestrator Opus review (resume) — bash skip"; return 1; fi
  if [ "$cls" = "MANUAL" ]; then
    orch_log "$gap: MANUAL — skipped (needs human judgement). Logged."
    runstate_set "$gap" "manual_skip" "" "needs human"; return 1
  fi
  if [ "$cls" = "CLAUDE" ]; then
    orch_log "$gap: CLAUDE-subagent task (orchestrator dispatches Opus design + Sonnet labelling) — bash wrapper SKIPS. Logged."
    runstate_set "$gap" "claude_subagent" "" "orchestrator Opus design + Sonnet labelling"; return 1
  fi
  return 0
}

if [ "$MODE" = "seq" ]; then
  for gap in $GAPS; do
    skip_or_run "$gap" || continue
    impl_one "$gap"; review_merge_one "$gap" || true
  done
else
  # parallel impl: AUTO concurrent (capped), LIVE one-at-a-time; then serial review+merge
  pids=()
  for gap in $GAPS; do
    skip_or_run "$gap" || continue
    if [ "$(gap_class "$gap")" = "LIVE" ]; then
      orch_log "$gap: LIVE — running serialized"; impl_one "$gap"
    else
      impl_one "$gap" & pids+=($!)
      while [ "$(jobs -rp | wc -l)" -ge "$CAP" ]; do wait -n 2>/dev/null || break; done
    fi
  done
  for p in "${pids[@]:-}"; do [ -n "$p" ] && wait "$p" 2>/dev/null || true; done
  for gap in $GAPS; do
    case "$(gap_class "$gap")" in MANUAL|CLAUDE) continue;; esac
    [ "$(runstate_get "$gap")" = "merged" ] && continue
    review_merge_one "$gap" || true
  done
fi

# Contract audit on the synced main. Exit 3 signals "do not advance" to run_night.sh.
CONTRACT_RC=0
CC="${CONTRACT_CMD[$WAVE]:-python -m pytest -q}"
if [ "$DRY" = 1 ]; then
  orch_log "DRY contract audit ($WAVE): $CC"
else
  sync_main; orch_log "contract audit ($WAVE): $CC"
  if ( cd "$REPO_ROOT" && eval "$CC" ) > "$EVID/contract_${WAVE}.log" 2>&1; then
    orch_log "contract $WAVE: PASS"
  else
    orch_log "contract $WAVE: FAIL (see $EVID/contract_${WAVE}.log)"; CONTRACT_RC=3
  fi
fi
orch_log "=== WAVE $WAVE done. run-state: $RUNSTATE"
exit $CONTRACT_RC

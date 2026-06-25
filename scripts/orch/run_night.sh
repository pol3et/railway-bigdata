#!/usr/bin/env bash
# Drive the unattended overnight run: preflight -> waves (in NIGHT_WAVES order) ->
# stop if a wave's contract fails. Resumable: re-running skips already-merged gaps
# (run-state ledger) so a crash/compaction does not lose progress.
#   scripts/orch/run_night.sh [--dry-run]
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib.sh"
source "$HERE/lib_run.sh"
source "$HERE/night.config.sh"
# DRY must be EMPTY (not "0") when not dry-running: it is consumed via ${DRY:+--dry-run}
# below, and ${VAR:+x} substitutes x whenever VAR is set & non-null — "0" is non-null.
DRY=; [ "${1:-}" = "--dry-run" ] && DRY=1
RUNSTATE="$EVID/run_state.json"; runstate_init

preflight() {
  local ok=1
  command -v codex >/dev/null      || { orch_log "PREFLIGHT FAIL: codex CLI not found"; ok=0; }
  command -v gh    >/dev/null      || { orch_log "PREFLIGHT FAIL: gh not found"; ok=0; }
  ensure_pol3et                    || { orch_log "PREFLIGHT FAIL: gh pol3et write auth"; ok=0; }
  ensure_minio                     || { orch_log "PREFLIGHT FAIL: MinIO"; ok=0; }
  # Ollama is only required if any LIVE/Ollama gap will run tonight.
  if printf '%s\n' "${GAP_CLASS[@]}" | grep -q LIVE; then
    if ! curl -fsS "${OLLAMA_HOST:-http://localhost:11434}/api/tags" >/dev/null 2>&1; then
      orch_log "PREFLIGHT WARN: Ollama not reachable — LIVE gaps (GAP-033 etc.) will PARK"
    else
      orch_log "preflight: Ollama reachable"
    fi
  fi
  ( cd "$REPO_ROOT" && git status --porcelain | grep -q . ) \
    && orch_log "PREFLIGHT WARN: main checkout is dirty — commit/stash before the run" || true
  [ "$ok" = 1 ]
}

if ! preflight && [ "$DRY" != 1 ]; then orch_log "preflight failed — aborting"; exit 1; fi

START="$(date '+%Y-%m-%d %H:%M:%S')"
for spec in $NIGHT_WAVES; do
  wave="${spec%%:*}"; mode="${spec##*:}"
  "$HERE/run_wave.sh" "$wave" "$mode" ${DRY:+--dry-run}; rc=$?
  if [ "$DRY" != 1 ] && [ "$rc" -eq 3 ]; then
    orch_log "STOP: wave $wave contract failed — not advancing. Inspect + resume after fix."
    break
  fi
done

# WAVE_LOG summary (real runs only)
if [ "$DRY" != 1 ]; then
  LOG="$REPO_ROOT/docs/WAVE_LOG.md"
  {
    echo ""; echo "## Overnight run — started $START"
    echo ""; echo '```'; cat "$RUNSTATE"; echo '```'
  } >> "$LOG" 2>/dev/null || true
fi
orch_log "NIGHT RUN COMPLETE. Ledger: $RUNSTATE  Summary appended to docs/WAVE_LOG.md (real runs)"
orch_log "Morning review: any gap with status parked_* has an OPEN PR awaiting you; manual_skip gaps need human work."

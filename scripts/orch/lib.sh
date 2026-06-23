#!/usr/bin/env bash
# Shared helpers for the Claude-orchestrator / Codex-implementer wave loop.
# POSIX-ish bash (Git Bash on Windows). JSON parsing uses python (always present),
# not jq (may be absent).
set -uo pipefail
export PYTHONUTF8=1   # specs/docs contain →, ✓, — etc.; force UTF-8 stdout on Windows cp1251

ORCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$ORCH_ROOT/../.." && pwd)"
EVID="$REPO_ROOT/output/evidence/orch"
mkdir -p "$EVID"

orch_log() { printf '[orch %s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }

# --- environment preconditions ---------------------------------------------
ensure_pol3et() {
  # Codex inherits gh/git identity from the env; pushing + PRs need write access.
  local active
  active="$(gh auth status 2>&1 | grep -i 'active account' || true)"
  if ! gh auth status 2>&1 | grep -q 'pol3et'; then
    orch_log "gh: pol3et not logged in — run 'gh auth login' as pol3et first"; return 1
  fi
  gh auth switch --user pol3et >/dev/null 2>&1 || true
  orch_log "gh active -> pol3et (was: ${active:-unknown})"
}
restore_cul8err() { gh auth switch --user cul8err >/dev/null 2>&1 || true; }

ensure_minio() {
  if ! docker compose -f "$REPO_ROOT/docker-compose.yml" ps 2>/dev/null | grep -q 'railway-minio'; then
    orch_log "bringing up MinIO"
    (cd "$REPO_ROOT" && docker compose up -d >/dev/null 2>&1) || { orch_log "MinIO up failed"; return 1; }
  fi
  orch_log "MinIO up"
}

# --- JSONL outcome parsing (codex exec --json) ------------------------------
codex_thread_id() {  # <run.jsonl> -> prints thread_id
  python - "$1" <<'PY'
import json,sys
for line in open(sys.argv[1],encoding="utf-8"):
    line=line.strip()
    if not line: continue
    try: e=json.loads(line)
    except Exception: continue
    if e.get("type")=="thread.started":
        print(e.get("thread_id","")); break
PY
}

codex_ok() {  # <run.jsonl> -> exit 0 if a turn.completed and no turn.failed/error
  python - "$1" <<'PY'
import json,sys
done=fail=False
for line in open(sys.argv[1],encoding="utf-8"):
    line=line.strip()
    if not line: continue
    try: e=json.loads(line)
    except Exception: continue
    t=e.get("type")
    if t=="turn.completed": done=True
    if t in ("turn.failed","error"): fail=True
sys.exit(0 if (done and not fail) else 1)
PY
}

# Extract one gap section "### GAP-0XX ..." from docs/GAP_TASKS.md
gap_spec() {  # <GAP-ID>
  python - "$REPO_ROOT/docs/GAP_TASKS.md" "$1" <<'PY'
import sys,re
text=open(sys.argv[1],encoding="utf-8").read()
gid=sys.argv[2]
m=re.search(rf"(^### {re.escape(gid)} .*?)(?=^### GAP-|\Z)", text, re.S|re.M)
sys.stdout.write(m.group(1).strip() if m else f"(no spec found for {gid})")
PY
}

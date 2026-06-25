#!/usr/bin/env bash
# Helpers for the UNATTENDED wave runner (run_wave.sh / run_night.sh).
# Layered on top of lib.sh. Pure bash + python (no jq). Sourced, not executed.

# JDK for the post-merge full-suite re-run (Spark tests skip without winutils).
export JAVA_HOME="${JAVA_HOME:-C:\\Program Files\\Eclipse Adoptium\\jdk-21.0.11.10-hotspot}"
# Ollama on the GTX 1060 (Pascal sm_61): the format=json GPU path crashes WITH flash attention
# (Pascal has no tensor cores) but runs 100% on GPU with it OFF (verified 2026-06-25; ollama#4979).
# So keep the GPU and disable flash attention; leave KV cache f16 (quantized KV without FA -> OOM,
# ollama#11471). Codex implementers inherit this. Pin Ollama 0.30.9 (Pascal routed to cuda_v12 per
# PR#12300; later cuda_v13 builds may drop the 1060). Do NOT force OLLAMA_NUM_GPU=0 (slow CPU fallback).
export OLLAMA_FLASH_ATTENTION="${OLLAMA_FLASH_ATTENTION:-0}"
# Load-tested stable context for the news pass: num_ctx=4096 leaves ~1.4 GB VRAM headroom and ran
# 24/24 format=json with zero crashes (8192 left ~0.8 GB and crashed 1/30 on the cold request).
# News texts are short snippets, so 4096 is ample. The pipeline (GAP-050) should also warm-up once
# + retry transient CUDA/transport errors (the Ollama runner self-recovers).
export OLLAMA_NUM_CTX="${OLLAMA_NUM_CTX:-4096}"

# --- implementer verdict / review JSON decisions -----------------------------
# Exit 0 only if the implementer verdict is clean enough to consider merging.
verdict_clean() {  # <verdict.json>
  python - "$1" <<'PY'
import json,sys
try: v=json.load(open(sys.argv[1],encoding="utf-8"))
except Exception: sys.exit(2)
if v.get("blocked"): sys.exit(1)
if not v.get("mergeable"): sys.exit(1)
if not v.get("pr_number"): sys.exit(1)
t=v.get("tests",{}) or {}
fs=str(t.get("full_suite","")).lower()
if "fail" in fs or "error" in fs: sys.exit(1)
if "passed" not in fs and t.get("unit")!="pass": sys.exit(1)
if t.get("unit")=="fail" or t.get("integration")=="fail": sys.exit(1)
sys.exit(0)
PY
}

# Exit 0 only if the review approves with no P1/P2 finding.
review_clean() {  # <review.json>
  python - "$1" <<'PY'
import json,sys
try: r=json.load(open(sys.argv[1],encoding="utf-8"))
except Exception: sys.exit(2)
if r.get("verdict")!="approve": sys.exit(1)
for f in (r.get("findings") or []):
    if str(f.get("priority","")).upper() in ("P1","P2"): sys.exit(1)
sys.exit(0)
PY
}

pr_number_of() {  # <verdict.json> -> prints PR number or empty
  python - "$1" <<'PY'
import json,sys
try: v=json.load(open(sys.argv[1],encoding="utf-8"))
except Exception: v={}
print(v.get("pr_number") or "")
PY
}

blocker_of() {  # <verdict.json> -> prints blocker text or empty
  python - "$1" <<'PY'
import json,sys
try: v=json.load(open(sys.argv[1],encoding="utf-8"))
except Exception: v={}
print((v.get("blocker") or "")[:300])
PY
}

# --- durable run-state ledger (survives orchestrator context compaction) -----
# RUNSTATE is set by the caller (run_wave/run_night). Map: gap -> {status,pr,note}.
runstate_init() { [ -f "$RUNSTATE" ] || printf '{}' > "$RUNSTATE"; }
runstate_set() {  # <gap> <status> [pr] [note]
  python - "$RUNSTATE" "$1" "$2" "${3:-}" "${4:-}" <<'PY'
import json,sys
f,gap,status,pr,note=sys.argv[1:6]
try: d=json.load(open(f,encoding="utf-8"))
except Exception: d={}
d[gap]={"status":status,"pr":pr,"note":note}
json.dump(d,open(f,"w",encoding="utf-8"),indent=2,ensure_ascii=False)
PY
}
runstate_get() {  # <gap> -> prints status (empty if unknown)
  python - "$RUNSTATE" "$1" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1],encoding="utf-8"))
except Exception: d={}
print((d.get(sys.argv[2]) or {}).get("status",""))
PY
}

# --- main-checkout sync + post-merge gate ------------------------------------
sync_main() {  # fast-forward the orchestrator's main checkout to origin/main
  git -C "$REPO_ROOT" fetch origin main >/dev/null 2>&1 || true
  git -C "$REPO_ROOT" merge --ff-only origin/main >/dev/null 2>&1 \
    || orch_log "WARN: main checkout not fast-forwardable (uncommitted work?)"
}
main_suite_green() {  # run the full suite on the orchestrator's main checkout
  ( cd "$REPO_ROOT" && python -m pytest -q ) > "$EVID/main_pytest.log" 2>&1
  local rc=$?
  tail -1 "$EVID/main_pytest.log" | sed 's/^/[orch main pytest] /' >&2
  return $rc
}

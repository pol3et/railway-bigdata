# Overnight autonomous run — readiness, recipes & go/no-go

> Purpose: everything needed to launch the orchestration unattended, sleep, and wake to merged,
> tested PRs. Authored 2026-06-25 after a live simulation + machine probe. Companion to
> `docs/ORCHESTRATION.md` (topology), `docs/ROADMAP_NEWS_TO_REPORT.md` (what), `docs/GAP_TASKS.md` (per-gap specs).
> The unattended driver is `scripts/orch/run_night.sh` (config `scripts/orch/night.config.sh`).

## Verified machine state (2026-06-25)

| Component | State | Note |
|---|---|---|
| **Codex exec under sandbox-bypass** | ✅ **WORKS** | Probe: `codex exec --dangerously-bypass-approvals-and-sandbox` ran python+git and **committed locally** via pwsh.exe. The old `CreateProcessAsUserW` block is gone with the flag. Codex can self-test + commit + push. |
| codex CLI | ✅ 0.142.0 | ChatGPT auth working (probe completed a turn). |
| gh auth | ✅ pol3et + cul8err | pol3et has `repo`,`workflow` (write). `ensure_pol3et` switches before implementers. |
| MinIO | ✅ up | `railway-minio` container, ports 9000-9001. |
| **Ollama** | ✅ installed 0.30.9, **serving** | `/api/tags` → 200. Model `qwen3:4b` pulling. **`OLLAMA_MODEL` default fixed → `qwen3:4b`** (was `qwen3.5:9b-q8_0`, too big for 6 GB). |
| GPU | ✅ GTX 1060 6 GB | 4.7 GB free, driver 581.42. Fits qwen3:4b-q4 (~2.6 GB) **or** one encoder — never both at once. |
| Python | 3.14 (main pipeline) + **3.11 (torch 2.1.1+cu118, CUDA available)** | No 3.12; the 3.11 env is the GPU **sidecar base**. |
| HF cache | `intfloat/multilingual-e5-large` already cached | e5-base/XLM-R still need a one-time pull. |
| JDK | ✅ 21 at `C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot` | `JAVA_HOME` **not exported** — the runner sets it. |
| Spark winutils | ❌ absent | Spark **writes** skip on native Windows → **Session C (Spark EDA/report) deferred** to a separate supervised session. |
| Disk | ✅ 68.5 GB free | enough for worktrees + models. |

## Scope tonight: Sessions A + B only (Session C deferred)

The Spark EDA→hypotheses→report finale (GAP-046/048/049) and the eval golden set (GAP-043) need
human judgement / hand-labelled data and/or winutils — they are **parked**, not auto-run. Tonight:

- **AUTO** (build + mock/fixture tests, auto-merge on clean verdict + approving review):
  GAP-039, GAP-050, GAP-035, GAP-034, GAP-031, GAP-040, GAP-044, GAP-045, GAP-041, GAP-042, GAP-047, GAP-043.
- **LIVE** (serialized, need the GPU/Ollama): GAP-033 (first real LLM run), GAP-036 (embeddings).
- **MANUAL** (skipped + logged — need you): GAP-037 (clustering), GAP-038 (NER),
  GAP-046 / GAP-048 / GAP-049 (Session C judgement).
- **GAP-043 eval — now AUTO (owner decision 2026-06-25):** the golden set is **created + labelled by an
  agent** (Codex/Sonnet — a *stronger* model than the evaluated `qwen3:4b`, never the pipeline model, to
  avoid self-evaluation circularity). Labels are agent silver-standard, not human gold → gate on
  **non-regression**, report absolute numbers as indicative. See the GAP-043 spec note in `docs/GAP_TASKS.md`.

Classification lives in `scripts/orch/night.config.sh` — edit it to move a gap in/out of scope.

## How the unattended runner behaves (`scripts/orch/run_night.sh`)

1. **Preflight**: codex, gh(pol3et), MinIO, Ollama-reachable, clean main. Aborts on hard fail.
2. **Waves in order** `6a(seq) → 6b(par) → B(par)` from `night.config.sh`:
   - **6a sequential** (dependency chain 039→050→033): implement → review → merge each before the next.
   - **6b/B parallel**: AUTO implementers run concurrently (cap `ORCH_PAR_CAP=3`); **LIVE gaps run one
     at a time** (single-box GPU rule); then review + merge each **serially**.
3. **Per gap**: `codex_impl.sh` → if verdict not clean, **one auto-resume** → `codex_review.sh`.
4. **Auto-merge gate** (all must hold, else the PR is left OPEN and the gap **parked**):
   `mergeable=true` + `blocked=false` + suite green + review `approve` + **no P1/P2** finding.
   After each merge: sync main + re-run the full suite; a red suite raises a loud `merged_suite_red` alarm.
5. **Contract audit** per wave (full suite on main); a FAIL **stops advancing** (exit 3).
6. **Durable ledger** `output/evidence/orch/run_state.json` (per-gap status+PR). **Re-running resumes** —
   merged gaps are skipped — so a crash or context-compaction never loses progress.
7. Morning: `parked_*` = an OPEN PR awaiting your call; `manual_skip` = needs you; `merged` = done.

```bash
# dry-run the plan (no codex, no merges) — always do this first:
bash scripts/orch/run_night.sh --dry-run
# real run (unattended). Orchestrator session must be in an auto-approve / bypass-permissions mode
# so its own Bash/gh calls don't block on prompts:
bash scripts/orch/run_night.sh
```

> The legacy "CHECKPOINT — pause for my approval" gate in the kickoff doc is **replaced** for AUTO/LIVE
> gaps by the auto-merge gate above. You authorise overnight self-merge by running `run_night.sh`.

## Recipe A — Ollama (the live LLM for GAP-033)

```powershell
# Server (Windows app auto-starts; manual start if needed):
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve      # or just launch the Ollama tray app
# Model (single-box default; q4_K_M ~2.6 GB, fits the 1060):
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull qwen3:4b
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" list        # confirm qwen3:4b present
# Smoke a JSON extraction (what the news pipeline does — temp 0, format=json):
$body = @{ model="qwen3:4b"; stream=$false; format="json"; options=@{temperature=0}
  messages=@(@{role="user"; content="Reply with JSON {""is_rail_related"": true} only."}) } | ConvertTo-Json -Depth 6
(Invoke-RestMethod -Uri http://localhost:11434/api/chat -Method Post -Body $body -ContentType "application/json").message.content
```
- **⚠️ Run the LLM on CPU (`OLLAMA_NUM_GPU=0`).** Verified 2026-06-25: on the GTX 1060 (Pascal sm_61)
  the **GPU `format=json` path crashes** with `CUDA error: an illegal memory access was encountered`
  (the plain generate path works on GPU, but the pipeline needs JSON mode). On **CPU it works and returns
  valid JSON** (e.g. `{"is_rail_related":true,"country":"HU",...}`) at **~16 s/article** — fine for the
  small one-time cached pass. The knob is wired: `ollama_client` sends `options.num_gpu` only when
  `OLLAMA_NUM_GPU` is set, and `lib_run.sh` exports `OLLAMA_NUM_GPU=0` so implementers inherit it.
  (Optional time-boxed GPU-speed experiment: driver ≥570 is met (581.42); restart `ollama serve` with
  `OLLAMA_FLASH_ATTENTION=0` — flash-attn is broken on Pascal — but it may not fix the JSON path and can
  balloon the compute graph past 6 GB, so keep CPU on the critical path. **vLLM is ruled out**: it needs
  compute capability ≥7.0 and the GTX 1060 is 6.1 (Linux/WSL doesn't bypass that). The only real Pascal-GPU
  option is llama.cpp/KoboldCpp with GBNF + FA off. Full sourcing:
  `.planning/coursework/research/bigdata/llm-serving-vllm-vs-ollama-pascal-2026-06-25.md`.)
- Config: `OLLAMA_HOST` (default `http://localhost:11434`), `OLLAMA_MODEL=qwen3:4b` (now the code default).
- Memory hygiene (single box): `ollama stop qwen3:4b` (or `OLLAMA_KEEP_ALIVE=0`) **before** any GPU encoder
  pass; confirm `ollama ps` empty so the sidecar gets the VRAM.
- The repo entrypoint is the pipeline's news extraction (`src/railway_lakehouse/silver/news/extract.py`
  via `ollama_client`); GAP-033's spec drives the exact bounded live command + evidence manifest.

## Recipe B — GPU encoder sidecar (for GAP-034 sentiment / GAP-036 embeddings)

✅ **Built + verified 2026-06-25**: venv at `output/runtime/sidecar-venv` (gitignored), `torch 2.1.1+cu118`
(GPU available), `multilingual-e5-base` encodes (768-dim). **Do NOT use `--force-reinstall` or `-U`** — they
clobber the cu118 torch with a CPU torch and trigger a numpy ABI break. Re-create cleanly with:
```powershell
$PY311 = "C:\Users\XxX360QUICKSCOPERXxX\pyver\311\python.exe"
& $PY311 -m venv --system-site-packages output\runtime\sidecar-venv
$SC = "output\runtime\sidecar-venv\Scripts\python.exe"
# PIN versions for the box's torch 2.1.1+cu118 — latest transformers/sentence-transformers break on
# import with this old torch ("NameError: name 'nn' is not defined"). Verified-compatible pins:
& $SC -m pip install "transformers==4.40.2" "sentence-transformers==2.7.0" "huggingface_hub==0.23.5" pyarrow pandas
# (language-id: add fasttext-wheel, or use lingua-py — pure-Python fallback, no compiler)
# Pre-cache weights once (HF reachable on the host; avoids a mid-night download):
& $SC -c "from sentence_transformers import SentenceTransformer as S; S('intfloat/multilingual-e5-base')"
& $SC -c "from transformers import AutoModelForSequenceClassification as M, AutoTokenizer as T; n='cardiffnlp/twitter-xlm-roberta-base-sentiment'; M.from_pretrained(n); T.from_pretrained(n)"
# Smoke (confirm GPU + embedding dim):
& $SC -c "import torch; from sentence_transformers import SentenceTransformer as S; m=S('intfloat/multilingual-e5-base'); v=m.encode(['query: vasút']); print('cuda',torch.cuda.is_available(),'dim',len(v[0]))"
```
- Pattern: the main Py3.14 pipeline **never imports torch**; it shells out to the sidecar
  (text parquet → embedding/sentiment parquet) and the subprocess **exits to free VRAM**. The sidecar
  CLI itself is GAP-036's deliverable; this recipe provisions its environment + weights.
- CPU fallback is acceptable for the small corpus if the GPU is busy (`--device cpu`).

## Open decisions — locked to the recommended defaults for the unattended run

So implementers don't guess (see `docs/SPEC_NEWS_PREPROCESSING.md` §8 / Appendix D):
embedder = `multilingual-e5-base` (config knob); torch = CPU-first, GPU sidecar (3.11+cu118) when free;
dedup = date-window blocking (NOT country), deterministic edge order, field-union; NER = gazetteer + GKG-orgs
first; clustering = separate artifact (not a Gold column); monetary = store `monetary_raw`+currency, defer FX;
golden bodies = hashes/excerpts/fetch-fixture (copyright). HU sentiment = XLM-R + golden offset (no hard gate v1).

## Morning review checklist

- `cat output/evidence/orch/run_state.json` — per-gap status.
- `merged` → done (verify the contract items in `docs/TASKS.md` Contracts D/E by eye).
- `parked_review` / `parked_impl` / `parked_merge` → open PR; read `output/evidence/orch/<gap>/{verdict,review}.json`.
- `merged_suite_red` → **act first**: a merge broke main (`output/evidence/orch/main_pytest.log`).
- `manual_skip` → the human-judgement work (golden set, hypotheses, report, Session C).
- `gh auth switch cul8err` to restore your default identity.

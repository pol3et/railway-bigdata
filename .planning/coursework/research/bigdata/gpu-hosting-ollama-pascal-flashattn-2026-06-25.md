# GPU hosting Qwen3-4B (structured JSON) on GTX 1060 / Pascal via Ollama — durable config (2026-06-25)

> Skill: `research-orchestrator`. Routed providers: **Tavily** (search), **Exa** (GitHub issue/PR search).
> Empirically confirmed on this box first, then cross-checked against Ollama docs + GitHub issues/PRs.

## Problem
Qwen3-4B `format=json` (grammar-constrained) extraction on a GTX 1060 6 GB (Pascal, cc 6.1, sm_61), Windows,
Ollama 0.30.9. With flash attention ON the GPU path crashes: `CUDA error: an illegal memory access was
encountered`. Need a durable, safe GPU config (CPU at ~16 s/article is too slow per owner).

## Findings (cited)
1. **Flash attention is broken on Pascal — disable it.** ollama#4979 (a GTX 1060 6 GB, Windows): crash only
   when `OLLAMA_FLASH_ATTENTION` is enabled; "Pascal gpus do not officially support flash attention due to
   their lack of tensor cores"; maintainer: FA is off-by-default, the env var is an opt-in. Fix = keep FA off
   (`OLLAMA_FLASH_ATTENTION=0`). https://github.com/ollama/ollama/issues/4979
   - **Verified on this box (2026-06-25):** FA off → `format=json` runs 100% on GPU, 4.0 GB resident, valid
     JSON; FA on → CUDA illegal memory access.
2. **Do NOT quantize the KV cache without flash attention.** ollama#11471: `WARN "quantized kv cache requested
   but flash attention disabled"` → `CUDA error: out of memory`. Leave `OLLAMA_KV_CACHE_TYPE` unset (default
   f16). https://github.com/ollama/ollama/issues/11471
3. **Driver floor met.** Ollama docs: "Nvidia GPUs with compute capability 5.0 through 6.2 require driver
   version 570 or newer." This box runs 581.42. https://docs.ollama.com/gpu
4. **Pascal is intentionally routed to the cuda_v12 backend (not v13).** ollama PR #12300 (merged 2025-09-16,
   maintainer dhiltgen): "Prioritize GPU compute capability over driver version to ensure Pascal GPUs (CC 6.1)
   use compatible CUDA v12 libraries instead of v13." Matches our serve log (`cuda_v13` archs [750,890,1000,
   1200] skips cc=610 → falls back to `cuda_v12`). https://github.com/ollama/ollama/pull/12300
   - **Version risk:** the cuda_v13 transition has regressed older cards across releases — #12332 ("ggml was
     not compiled with any CUDA arch <= 700"), #12341 ("v0.11.x no kernel image; v0.10.1 fine"), #14188
     ("Crashes RTX 3060 on cuda_v13 v0.13.0–v0.15.6"). → **Pin the working version (0.30.9); disable
     auto-update.** https://github.com/ollama/ollama/issues/12332 · /12341 · /14188
5. **`OLLAMA_NUM_GPU=0` is the CPU fallback only.** ollama#15863: forcing it "resolves the crash but makes the
   tool unusable due to extremely slow inference." Now that the GPU path works, do NOT force it.
   https://github.com/ollama/ollama/issues/15863

## Recommended durable config (this box)
- **Ollama 0.30.9, pinned** (do not auto-update; a future cuda_v13-only build could drop the 1060).
- Env (persisted via `setx`, inherited by the Ollama app + the orchestration runner):
  - `OLLAMA_FLASH_ATTENTION=0`  (REQUIRED on Pascal)
  - leave `OLLAMA_KV_CACHE_TYPE` **unset** (f16) — never q8_0/q4_0 without FA
  - leave `OLLAMA_NUM_GPU` **unset** (GPU placement); the repo's knob = CPU fallback only
  - driver ≥ 570 (have 581.42)
- `OLLAMA_MODEL=qwen3:4b`, `num_ctx=8192` fits (4.0 GB resident, ~0.8 GB free); use `num_ctx=4096` for extra
  headroom under sustained batches (news texts are short snippets — 4096 is ample).
- Future-proofing if a later Ollama drops cuda_v12: **llama.cpp server** (Pascal/cc 6.1 supported, GBNF JSON)
  is the fallback host.

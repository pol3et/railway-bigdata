# LLM Serving: vLLM vs Ollama vs alternatives on GTX 1060 6GB (Pascal sm_61) for Qwen3-4B JSON output

> Research method: `research-orchestrator` skill (forced search-before-answer).
> Routed MCP providers used: **Tavily** (tavily_search, tavily_extract) and **Exa** (web_search_exa).
> Date: 2026-06-25. Course: bigdata / course_proj (news feature extraction).

## Scope / hardware (exact box)
- GPU: NVIDIA GTX 1060 6GB. Pascal, CUDA compute capability **6.1 (sm_61)**, no Tensor Cores. ~4.7 GB VRAM free.
- OS: Windows 10. Python 3.11 + torch 2.1.1+cu118 (CUDA works); also Python 3.14.
- Goal: serve **Qwen3-4B (q4-class quant)** for **schema-constrained JSON** (news feature extraction). ~hundreds of articles, one-time cached pass. Tiny corpus -> GPU acceleration is nice-to-have, not required.
- Current state: **Ollama 0.30.9** works. GPU path **crashes on `format=json`** with `CUDA error: an illegal memory access was encountered` (grammar-constrained sampling). Plain (non-JSON) GPU generate works. **CPU path works**, valid JSON at ~16 s/article.

## Queries run
- "vLLM minimum GPU compute capability requirement 7.0 Volta Pascal sm_61 not supported" (Tavily)
- "vLLM Windows native support WSL2 required installation" (Tavily)
- "Ollama format json CUDA error illegal memory access GTX 1060 Pascal flash attention grammar" (Tavily)
- "Ollama OLLAMA_FLASH_ATTENTION disable Pascal ... CUDA illegal memory access fix older GPU" (Tavily)
- "KoboldCpp llama.cpp lmdeploy TGI compute capability 6.1 Pascal GTX 1060 GBNF grammar" (Tavily)
- "GitHub issue Ollama format=json CUDA illegal memory access grammar sampling GTX 1060 Pascal flash attention disable fix" (Exa)
- "llama.cpp flash attention Pascal sm_61 not supported requires Turing tensor cores GTX 1060 grammar sampling crash" (Tavily)
- "GitHub ollama issue Pascal GPU format json structured output grammar CUDA illegal memory access ... works on CPU 2025" (Exa)
- Extracts: docs.ollama.com/gpu and github.com/SystemPanic/vllm-windows (Tavily extract)

---

## Q1. vLLM minimum GPU compute capability — does it support Pascal sm_61?

**No. vLLM requires compute capability 7.0 (Volta) or higher. Pascal sm_61 is NOT supported.** This is stated identically across every official vLLM docs version checked:

- vLLM GPU install docs (v0.10.2, current line): "GPU: compute capability 7.0 or higher (e.g., V100, T4, RTX20xx, A100, L4, H100, etc.)" — https://docs.vllm.ai/en/v0.10.2/getting_started/installation/gpu.html
- vLLM GPU docs (v0.7.0): same requirement, "compute capability 7.0 or higher" — https://docs.vllm.ai/en/v0.7.0/getting_started/installation/gpu/index.html
- vLLM docs (v0.4.2): "GPU: compute capability 7.0 or higher (e.g., V100, T4, RTX20xx, A100, L4, H100, etc.)" — https://docs.vllm.ai/en/v0.4.2/getting_started/installation.html
- vLLM official forum staff answer: "vLLM requires GPUs with compute capability 7.0 or higher (Volta or newer)." — https://discuss.vllm.ai/t/vllm-on-rtx5090-working-gpu-setup-with-torch-2-9-0-cu128/1492

Pascal-specific confirmation:
- GitHub issue #1431 "Why are GPUs with compute capability below 7.0 are not supported" — opened by a user with **CC 6.1** asking about a Tesla P4. https://github.com/vllm-project/vllm/issues/1431
- GitHub issue #963 "Support for compute capability <7.0" (P100 / 6.0). https://github.com/vllm-project/vllm/issues/963

Why: CC < 7.0 lacks the f16 instruction support vLLM kernels assume; building for sm_61 throws "f16 arithmetic and compare instructions require .target sm_53 or higher" type errors and, more fundamentally, vLLM's CUDA kernels and flash-attention paths assume Volta+ (Tensor Cores). (forum thread above). Pascal also has no Tensor Cores — community consensus is Volta 7.0 is the practical floor for "modern stacks" (flash attention, triton). https://news.ycombinator.com/item?id=39987013

**Any build that runs on sm_61?** No supported/maintained one. There are no official pre-built wheels for CC < 7.0, and a source build hits the f16/kernel target errors above. The cost would be: forking + patching kernels for sm_61 with no upstream support, almost certainly failing on flash-attention and quant kernels. Not viable for a coursework deadline.

## Q2. vLLM on Windows — native, or WSL2/Docker/Linux?

**No native Windows support. vLLM officially targets Linux only.** Official requirement: "OS: Linux" (every GPU install doc, e.g. v0.10.2 / v0.7.0 / v0.4.2 above).

- Running on Windows is done via **WSL2** (Ubuntu) or **Docker Desktop + WSL2**:
  - Community WSL2 guide — https://mobiarch.wordpress.com/2025/10/02/install-vllm-in-wsl
  - "Making vLLM work on WSL2" — https://dev.to/docteurrs/making-vllm-work-on-wsl2-482e
  - Docker Model Runner now supports vLLM on Docker Desktop for Windows "with WSL2 and NVIDIA GPUs" — https://www.docker.com/blog/docker-model-runner-vllm-windows
- An unofficial native-Windows fork exists (`SystemPanic/vllm-windows`) but it is built/tested for new GPUs (RTX 5090 / Blackwell); its notes explicitly disable FA3 on Windows and it is not aimed at Pascal. https://github.com/SystemPanic/vllm-windows

Even via WSL2, the CC 7.0 floor from Q1 still applies — WSL2 passes through the same GTX 1060 sm_61 GPU, so it does not help.

## Q3. Conclusion on vLLM for THIS box

**vLLM cannot run GPU inference on a GTX 1060 (sm_61).** The compute-capability floor (7.0) is a hard, documented requirement, and Windows needs WSL2/Docker anyway. **Do NOT recommend vLLM for this hardware.** (It would only become relevant if the user later moved to a Volta+ GPU on Linux/WSL2.)

## Q4. Qwen3-4B schema-constrained JSON serving (correct configs)

Two relevant stacks (vLLM is out per Q3, but documented for completeness; llama.cpp/Ollama is what actually runs here):

**vLLM guided/structured output** (FYI only):
- Backends: `xgrammar` (default) or `guidance`/LLGuidance; older versions also `outlines`, `lm-format-enforcer`. — https://docs.vllm.ai/en/latest/features/structured_outputs
- Params: `guided_json` (JSON schema), `guided_regex`, `guided_choice`, `guided_grammar`. In v0.12+ these moved under `structured_outputs` (`{"structured_outputs": {"json": ...}}`). `guided_decoding_backend` selects backend (e.g. `xgrammar:no-fallback`). — https://docs.vllm.ai/en/v0.8.2/features/structured_outputs.html
- Backend choice: simple/repetitive schemas -> XGrammar (precompute+cache, highest throughput); dynamic/complex schemas -> LLGuidance. — https://blog.squeezebits.com/guided-decoding-performance-vllm-sglang
- Known vLLM issue: xgrammar guided decoding can fail on some schemas / CPU backend (e.g. issue #31901 with Qwen3-4B-Instruct on macOS CPU). https://github.com/vllm-project/vllm/issues/31901

**llama.cpp / Ollama (what is actually relevant here):**
- llama.cpp constrains output with **GBNF grammars**; `format=json` in Ollama injects a hardcoded JSON grammar, and since Ollama v0.5 a JSON **schema** is compiled to a per-schema GBNF grammar passed to llama.cpp. — https://blog.danielclayton.co.uk/posts/ollama-structured-outputs
- Grammar-constrained decoding adds CPU-side overhead: token-mask generation per step is not GPU-parallelised, so it is slower and stresses a different code path than plain generation (relevant to the crash signature). (same source)

**Known issues with grammar-constrained decoding (directly relevant to the crash):**
- The whole `format`/grammar path is fragile in the llama.cpp/Ollama schema->GBNF converter. Multiple 2025 bugs: minified JSON schema fails (#10805, fixed by PR #10820 "add minimum memory for grammar"); escaped double-quotes break grammar (#11500); thinking-mode + structured output produces invalid JSON (#10929); "Undefined rule identifier 'space'" / "failed to load model vocabulary required for format" (OllamaSharp #245, ollama PR #10747/#10820). These show the grammar path is a distinct, error-prone subsystem.
  - https://github.com/ollama/ollama/issues/10805 , https://github.com/ollama/ollama/issues/11500 , https://github.com/ollama/ollama/issues/10929 , https://github.com/awaescher/OllamaSharp/issues/245
- For older GPUs specifically, the JSON/grammar path exercises GPU kernels (sampling/masking + attention) that Pascal handles less robustly; the `illegal memory access` family on Ollama GPU is widespread in 2025 and is often kernel/flash-attention/version-specific (see Q5).

## Q5. Ollama GPU crash on Pascal + `format=json` — workarounds

Background facts:
- Ollama **does** list Pascal CC 6.1 (incl. **GTX 1060**) as supported, but with a driver caveat: "Ollama supports Nvidia GPUs with compute capability 5.0+ and driver version 531 and newer. **Nvidia GPUs with compute capability 5.0 through 6.2 require driver version 570 or newer.**" GTX 1060 is explicitly in the 6.1 table. — https://docs.ollama.com/gpu  -> **First check: driver >= 570.**
- Pascal-specific Ollama breakage is real and version-sensitive: issue #12316 — GTX 1080 / GTX 1050 (both CC 6.1) on Windows got "CUDA error: no kernel image is available for execution on the device" running qwen3:4b; reported "fixed in 0.12.0" and a comment notes a build had **dropped CC 6.1 support**. https://github.com/ollama/ollama/issues/12316

**Flash attention is the prime suspect and the prime workaround:**
- **Flash Attention does not work on Pascal.** llama.cpp issue #7055: FA fails on a Pascal Quadro P3200 but "is working for me on a Turing GPU." https://github.com/ggml-org/llama.cpp/issues/7055 . HN: Volta 7.0 is the bare minimum for flash attention. https://news.ycombinator.com/item?id=39987013
- Ollama's FA path: when FA is enabled but unsupported, Ollama logs `flash attention enabled but not supported by gpu` and disables it; if you also set `OLLAMA_KV_CACHE_TYPE`, it warns `quantized kv cache requested but flash attention disabled`. — issue #11471 / #10167 logs. https://github.com/ollama/ollama/issues/11471 , https://github.com/ollama/ollama/issues/10167
- Disabling FA is a documented lever: `OLLAMA_FLASH_ATTENTION=0` (Windows PowerShell: `$env:OLLAMA_FLASH_ATTENTION=0`). KV-cache quantization is FA-dependent. — https://localllm.in/blog/ollama-vram-requirements-for-local-llms

**Would disabling flash attention plausibly fix the GPU JSON path on a GTX 1060? -> Plausible and worth trying, but not guaranteed.**
- Plausible: FA is unsupported on Pascal and is a known source of GPU instability; the `format=json` grammar path hits sampling/attention kernels harder, so an FA bug there is a credible cause of the illegal-memory-access. Forcing `OLLAMA_FLASH_ATTENTION=0` is low-cost.
- Caveat: In the closest documented analog (issue #14446, a crash that occurs only on a harder code path — vision — but not on plain text), `OLLAMA_FLASH_ATTENTION=0` did **not** fix the crash and caused the **compute graph to balloon** (e.g. 941 MiB -> 6.4 GiB) and GPU layer count to drop. On a 6 GB / ~4.7 GB-free card that ballooning could itself push you OOM and back to CPU. https://github.com/ollama/ollama/issues/14446
- The crash is also frequently fixed by a **version bump or driver/CUDA-toolkit update** rather than a flag (#12316 fixed in 0.12.0; #10555 introduced 0.6.8 fixed by 0.9.0; #9018 traced to CUDA-toolkit mismatch). So updating/downgrading Ollama is a parallel lever.

Concrete things to try (cheap, in order), all reversible env vars:
1. Confirm NVIDIA driver >= 570 (required for CC 6.1 on current Ollama). https://docs.ollama.com/gpu
2. `OLLAMA_FLASH_ATTENTION=0` (and do NOT set `OLLAMA_KV_CACHE_TYPE`, since quantized KV needs FA). https://github.com/ollama/ollama/issues/10167
3. Reduce `num_ctx` / `num_batch` and watch the FA-off compute-graph ballooning vs 4.7 GB free (#14446).
4. Try a different Ollama version (the crash is version-bound in several issues: #12316, #10555).
5. Use a q4_K_M GGUF (Qwen3-4B q4 ~2.4-2.7 GB weights, fits 4.7 GB with small ctx).

## Q6. Alternatives that DO support Pascal sm_61 for GPU-accelerated structured generation

- **llama.cpp (server, with GBNF / `--grammar` / `-j` JSON schema): supports Pascal sm_61.** llama.cpp README: the MMVQ kernel decision is made on compute capability "(MMVQ for **6.1/Pascal/GTX 1000** or higher)". https://cnb.cool/aigc/llama.cpp/-/blob/dae57a1ebc1c9bd5693ab999e19d77c5506ae559/README.md . Confirmed running on a GTX 1060 CC 6.1 with CUDA. https://stackoverflow.com/questions/76963311/llama-cpp-python-not-using-nvidia-gpu-cuda . Builds/runs on Windows (`llama-server.exe`, `llama-gbnf-validator.exe`). https://steelph0enix.github.io/posts/llama-cpp-guide . Note: **FA must stay off** on Pascal (#7055). For the escaped-quote grammar bugs, llama.cpp can be built with `-DLLAMA_LLGUIDANCE=ON` for a more robust constraint engine. https://github.com/ollama/ollama/issues/11500
- **KoboldCpp: supports Pascal.** It is a llama.cpp wrapper that advertises CUDA acceleration "even on low-end systems" / "as old as" mid-range hardware, single-exe on Windows, GGUF, grammar support inherited from llama.cpp. https://koboldcpp.com  (KoboldCpp ships dedicated CUDA builds covering older archs incl. Pascal; it is the usual recommendation for GTX 10-series on Windows.)
- **lmdeploy: effectively no.** Its TurboMind engine targets "Volta to Hopper"/sm_70+; sm_61 is not a supported target. (Same Tensor-Core-era floor as vLLM.) Treat as unsupported for this box.
- **TGI (HF text-generation-inference): no for this box.** TGI is Linux/Docker-first and its optimized kernels (flash-attention, paged attention) assume Ampere/Turing+ (>=7.5 for full features); it is not a fit for Pascal sm_61 on Windows.

So among GPU-accelerated structured-generation servers, only the **llama.cpp family (llama.cpp server, KoboldCpp — and Ollama, which is itself llama.cpp-based)** actually support Pascal 6.1 on Windows.

## Q7. Bottom-line recommendation for THIS box

Ranking (GTX 1060 6GB / Pascal / Windows / Qwen3-4B / JSON / tiny one-time corpus):

**#1 — (a) Accept Ollama CPU as the primary, shippable path. RECOMMENDED.**
- It already works and returns valid JSON at ~16 s/article. For "hundreds of articles, one-time cached pass," that is roughly tens of minutes to ~1-2 hours total — entirely acceptable for a one-shot cached job. Reliability/correctness of the JSON is the actual requirement; GPU speed is not. Lowest risk, zero new dependencies, no deadline exposure.

**#2 — (b) Try the Ollama GPU fix in parallel (cheap, reversible).** Specifically: driver >= 570, then `OLLAMA_FLASH_ATTENTION=0` (Q5). If it makes `format=json` stable on GPU without OOM ballooning (#14446 warns it might not), keep it as a speed bonus. Time-box this to ~30 min; if it still crashes or OOMs, fall back to #1. Do not block the coursework on it.

**#3 — (d) llama.cpp server or KoboldCpp directly, with GBNF/JSON-schema, FA off.** This is the best GPU-accelerated option that genuinely supports sm_61 on Windows (Q6). Worth it only if you want GPU speed and Ollama's GPU JSON path stays broken. KoboldCpp is the easiest (single Windows exe). Slightly more setup than #1/#2.

**#4 (DO NOT) — (c) vLLM.** Ruled out: requires CC >= 7.0 (Volta+); GTX 1060 is sm_61; no native Windows support (WSL2/Docker only, which doesn't change the CC floor). Not viable on this hardware (Q1-Q3).

**Reasoning:** The corpus is tiny and the pass is one-time and cached, so the dominant constraints are correctness and time-to-ship, not throughput. The CPU path satisfies both today. The GPU JSON crash is a known-fragile intersection (Pascal + flash-attention-incapable hardware + the error-prone llama.cpp grammar path); `OLLAMA_FLASH_ATTENTION=0` is the single highest-probability cheap fix but the closest documented analog shows it can fail and/or cause VRAM ballooning on a 6 GB card, so it must not be on the critical path. vLLM is a non-starter on sm_61.

## Key citations
- vLLM CC 7.0 floor: https://docs.vllm.ai/en/v0.10.2/getting_started/installation/gpu.html ; https://docs.vllm.ai/en/v0.7.0/getting_started/installation/gpu/index.html ; https://docs.vllm.ai/en/v0.4.2/getting_started/installation.html ; https://discuss.vllm.ai/t/vllm-on-rtx5090-working-gpu-setup-with-torch-2-9-0-cu128/1492
- vLLM Pascal issues: https://github.com/vllm-project/vllm/issues/1431 ; https://github.com/vllm-project/vllm/issues/963
- vLLM Windows/WSL2/Docker: https://www.docker.com/blog/docker-model-runner-vllm-windows ; https://dev.to/docteurrs/making-vllm-work-on-wsl2-482e ; https://github.com/SystemPanic/vllm-windows
- vLLM structured outputs: https://docs.vllm.ai/en/latest/features/structured_outputs ; https://docs.vllm.ai/en/v0.8.2/features/structured_outputs.html ; https://blog.squeezebits.com/guided-decoding-performance-vllm-sglang
- Ollama hardware support (CC 6.1 incl GTX 1060; driver 570+): https://docs.ollama.com/gpu
- Ollama Pascal crash / version-bound: https://github.com/ollama/ollama/issues/12316 ; https://github.com/ollama/ollama/issues/10555 ; https://github.com/ollama/ollama/issues/9018
- Flash attention off / not supported on Pascal: https://github.com/ggml-org/llama.cpp/issues/7055 ; https://github.com/ollama/ollama/issues/11471 ; https://github.com/ollama/ollama/issues/10167 ; https://github.com/ollama/ollama/issues/14446 ; https://news.ycombinator.com/item?id=39987013 ; https://localllm.in/blog/ollama-vram-requirements-for-local-llms
- Ollama grammar/JSON fragility: https://blog.danielclayton.co.uk/posts/ollama-structured-outputs ; https://github.com/ollama/ollama/issues/10805 ; https://github.com/ollama/ollama/issues/11500 ; https://github.com/ollama/ollama/issues/10929 ; https://github.com/awaescher/OllamaSharp/issues/245
- llama.cpp / KoboldCpp Pascal support + GBNF: https://cnb.cool/aigc/llama.cpp/-/blob/dae57a1ebc1c9bd5693ab999e19d77c5506ae559/README.md ; https://stackoverflow.com/questions/76963311/llama-cpp-python-not-using-nvidia-gpu-cuda ; https://steelph0enix.github.io/posts/llama-cpp-guide ; https://koboldcpp.com

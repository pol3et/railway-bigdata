# Qwen 3.5 Ollama Runtime Config - 2026-06-22

## Question

Should the project prefer `qwen3.5:9b`, which quantization should be used, what
runtime options are needed for reliable JSON extraction, and should we switch to
vLLM?

## Local Context First

Files reviewed:

- `src/railway_lakehouse/silver/config.py`
- `src/railway_lakehouse/silver/ollama_client.py`
- `src/railway_lakehouse/silver/stats/merge.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `tests/test_silver_characterization.py`
- `docs/SILVER_DESIGN.md`

Current local constraints:

- Ollama is used only for cached stats-label mapping and validated article
  extraction.
- Numeric rows stay deterministic and never pass through the LLM.
- The project needs reliable schema-shaped JSON more than high-throughput
  serving.

## MCP Research

MCP providers used:

- Tavily search/extract.
- Exa web search.
- Firecrawl search.
- Ref was attempted for exact docs but returned a credit-block response.

Sources checked:

- <https://ollama.com/library/qwen3.5/tags>
- <https://ollama.com/library/qwen3.5:9b-q8_0>
- <https://ollama.com/library/qwen3.5:9b-q4_K_M>
- <https://docs.ollama.com/api/chat>
- <https://docs.ollama.com/api/generate>
- <https://docs.ollama.com/capabilities/structured-outputs>
- <https://docs.ollama.com/capabilities/thinking>
- <https://qwen.readthedocs.io/en/latest/quantization/llama.cpp.html>
- <https://qwen.readthedocs.io/en/latest/deployment/vllm.html>
- <https://docs.vllm.ai/en/stable/features/structured_outputs>
- <https://github.com/ollama/ollama/issues/14793>
- <https://github.com/vllm-project/vllm/issues/18819>

## Findings

Ollama Qwen 3.5 tags:

- `qwen3.5:9b-q4_K_M`: 6.6 GB, Q4_K_M, 256K context window.
- `qwen3.5:9b-q8_0`: 11 GB, Q8_0, 256K context window.
- `qwen3.5:9b-bf16`: 19 GB, bf16, 256K context window.

Quantization:

- Qwen docs list Q8_0, Q5_K_M, and Q4_K_M as common GGUF/llama.cpp presets.
- Qwen docs warn that lower-bit quantization can reduce accuracy.
- llama.cpp discussion data characterizes Q4_K_M as balanced/recommended and
  Q8_0 as extremely low quality loss.
- Therefore Q8_0 is the quality-first quantized choice; Q4_K_M is the practical
  lower-memory fallback.

Ollama runtime config:

- Ollama chat/generate APIs support `format` as `json` or a JSON schema.
- Ollama structured-output docs recommend passing the schema and lowering
  temperature to `0` for deterministic completions.
- Ollama thinking docs define `think` as a top-level chat/generate field.
- Exa surfaced Ollama issue evidence that putting `think` inside `options` can
  silently fail for Qwen 3.5; top-level `think: false` is the safer shape.

vLLM:

- Qwen docs and vLLM docs support structured/JSON output.
- vLLM adds serving/GPU setup, OpenAI-compatible serving configuration, and
  Qwen thinking/template configuration.
- vLLM issue evidence shows Qwen guided JSON can fail in some
  `enable_thinking=false` setups.
- This project does not yet need batched high-throughput LLM serving.

## Decision

Use Ollama, not vLLM, for the default coursework runtime.

Set:

- `OLLAMA_MODEL=qwen3.5:9b-q8_0` by default.
- `OLLAMA_MODEL=qwen3.5:9b-q4_K_M` as the documented lower-memory fallback.
- `/api/chat` for JSON calls.
- `format` set to the JSON schema when present, otherwise `"json"`.
- top-level `think: false` by default.
- `temperature=0`.
- bounded defaults: `OLLAMA_NUM_CTX=8192`, `OLLAMA_NUM_PREDICT=1024`.

## Boundary

This research and code update does not prove a live Ollama install, model pull,
GPU/CPU performance, or extraction quality on real articles. Those claims need
separate executed evidence under `output/evidence/`.

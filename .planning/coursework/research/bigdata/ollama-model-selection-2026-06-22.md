# Ollama Model Selection - 2026-06-22

## Question

Why use the previous `llama3.1:8b` default instead of a newer Qwen or Gemma
model, and which model should the project select now?

## Local Context First

Files reviewed:

- `src/railway_lakehouse/silver/config.py`
- `src/railway_lakehouse/silver/ollama_client.py`
- `src/railway_lakehouse/silver/stats/merge.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/pipeline.py`
- `docs/SILVER_DESIGN.md`
- `docs/ARCHITECTURE.md`
- `docs/WORK_SPLIT.md`

Current repo use:

- Ollama is used only for cached source-label mapping and validated article
  extraction.
- Numeric stats rows are never rewritten by the LLM.
- The client is model-agnostic through `OLLAMA_MODEL`.
- Existing fixture E2E tests mock Ollama output or skip live extraction.

## External Research

Official Ollama pages checked:

- `llama3.1:8b`: 4.9 GB, 8.03B parameters, Q4_K_M.
- `qwen3:8b`: 5.2 GB, 8.19B parameters, Q4_K_M, Qwen family with broad
  multilingual instruction-following coverage.
- `qwen3.5:9b`: 6.6 GB, 256K context, newer Qwen 3.5 family.
- `gemma3:4b`: 3.3 GB, 128K context, compact local option.
- `gemma4`: current local models start larger for this project
  (`gemma4:e2b` 7.2 GB, `gemma4:e4b` 9.6 GB, `gemma4:12b` 7.6 GB).

Sources:

- <https://ollama.com/library/llama3.1:8b>
- <https://ollama.com/library/qwen3:8b>
- <https://ollama.com/library/qwen3.5>
- <https://ollama.com/library/gemma3>
- <https://ollama.com/library/gemma4>

## Decision

Set the project default to `qwen3:8b`.

Rationale:

- It stays in the same local-memory class as `llama3.1:8b` while moving to a
  Qwen model family better aligned with multilingual HU/DE/EN extraction.
- It is small enough for teammate laptops and CI-style local development.
- It keeps the existing Ollama client and validation boundary unchanged.

Document `OLLAMA_MODEL=qwen3.5:9b` as the preferred higher-quality local option
when 6.6 GB model memory is acceptable.

Document Gemma as an explicit experiment or low-memory alternative rather than
the default. Gemma 3 is compact, but the current Gemma 4 local models are larger
and include thinking/multimodal behavior that is not needed for deterministic
JSON extraction.

## Boundaries

This session selected and documented the model default. It did not run a live
Ollama server, download a model, or prove live extraction quality. Those claims
need separate executed evidence under `output/evidence/`.

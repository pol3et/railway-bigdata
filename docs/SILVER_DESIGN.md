# Silver layer — design, and why it is a *hybrid* (not "Ollama merges everything")

You asked for an Ollama-based Silver that (1) merges the statistical tables into one
table with English feature labels and (2) extracts a meaningful feature-style summary
from each news article. Below is what was built and the **alternative** to running an LLM
over the whole layer.

## The recommendation: use the LLM only where it adds information

| Silver task | Use an LLM? | Why |
|---|---|---|
| Merge/unpivot/join numeric stat tables | **No — deterministic pandas/PySpark** | LLMs hallucinate numbers, are slow, and are non-reproducible. Schema alignment and joins must be exact and re-runnable. |
| Translate/normalize column labels to canonical English | **Partly** | Eurostat labels are *already English* (its JSON-stat/DSD dimension labels) → no LLM. Only KSH (HU) and Statistik Austria (DE) headers need translation, done once and **cached** for review. |
| Turn each news article into structured features | **Yes** | Unstructured→structured extraction is exactly what LLMs are good at; output is JSON-constrained and validated. |
| News features that GDELT already provides | **No** | GDELT GKG ships themes, tone, locations, persons, organizations. Use them directly; reserve the LLM for RSS full-text and enrichment. |

**Net effect:** the LLM touches *labels* (a tiny, cached vocabulary) and *article text*,
never the numeric rows. This is the "LLM proposes the schema mapping, deterministic code
executes the merge" pattern.

## What was built

```
silver/
├── config.py          # Ollama host/model, canonical feature vocabulary, news taxonomy
├── ollama_client.py   # JSON-mode client: temperature=0, retries, validation-first (None on failure)
├── schema.py          # StatFact (merged stats row) + NewsFeature (per-article) + validators
├── stats/
│   └── merge.py       # deterministic readers (Eurostat/WB/tabular) + LLM-assisted cached
│                      #   crosswalk + deterministic merge into ONE unified long table
├── news/
│   └── extract.py     # Ollama per-article feature extraction + GDELT-GKG passthrough (no LLM)
└── run.py             # orchestrator: stats / news / all
```

### Merge target = long format
Each source is melted to `(geo, year, feature, value, unit, source_system, source_dataset,
source_column)`. One unified long table; **Gold** pivots it to a country-year feature matrix.
Long-format merge sidesteps the wide-schema alignment problem entirely and keeps full
provenance (which source/column each number came from).

### Crosswalk is a reviewable, cached artifact
`build_crosswalk()` maps each distinct source column to one canonical key (or `unmapped`,
which is dropped — never guessed). Eurostat/English labels map by rule (no LLM); HU/DE labels
go to Ollama once and are cached to `crosswalk_cache.json` so you can **review and commit** the
mapping instead of re-querying the model every run.

### News extraction is validated, not trusted
`extract_article()` returns JSON constrained to a schema; `validate_news_feature()` then coerces
it — unknown event types → `other`, unknown operators → `other`, bad numbers → `null`,
confidence clamped to [0,1]. A failed/unreachable model returns `None` and the article is
skipped and logged, so a few bad calls never abort the run or fabricate data.

## What was verified (offline, no Ollama)
Static tests pass for: the Eurostat melt-to-long reader (flag stripping, geo extraction), the
rule+LLM crosswalk (LLM stubbed), the merge into one unified table, schema validation hardening
deliberately-malformed LLM output, and the Ollama client's request shape + loose-JSON parsing
(code fences / leading prose tolerated).

## Known limitations / what you must wire
- **Ollama cannot run in the build sandbox** (local server + model download, network-locked), so
  live extraction/crosswalk calls were not executed — only the deterministic logic and a mocked
  client. Run the LLM paths inside your stack.
- **The Eurostat reader needs the DSD dimension labels** to turn dimension *codes* (e.g. `FRG`)
  into English feature names; the stub maps by label text. Load the `.dic`/JSON-stat labels that
  ship with each dataset so the rule-based crosswalk catches them without the LLM.
- **KSH/Statistik Austria/UIC raw parsers are not included** — `read_tabular_long()` expects an
  already-tidy `(label, year, value)` frame. The XLSX/JSON-stat parsing of those Bronze files is
  the next piece (mirrors how Bronze landed them).
- **MinIO I/O is stubbed in run.py** — wire your `s3fs` reads of Bronze and writes of the Silver
  tables exactly as the Bronze `RawLander` does.

## Model choice
`OLLAMA_MODEL` defaults to `qwen3:8b`. It replaces the older `llama3.1:8b`
placeholder because the Silver LLM tasks are multilingual HU/DE/EN label and
article extraction, not generic chat. Official Ollama metadata puts
`llama3.1:8b` at 4.9 GB and `qwen3:8b` at 5.2 GB, so this keeps the same
local-memory class while using a Qwen model family that advertises broad
multilingual instruction-following coverage.

Use `OLLAMA_MODEL=qwen3.5:9b` when the local machine can afford the larger
6.6 GB model and the team wants the newer Qwen line for higher-quality
extraction. Use Gemma only as an explicit experiment or low-memory alternative:
`gemma3:4b` is smaller, while current Gemma 4 local models are larger and add
thinking/multimodal behavior we do not need for validated JSON extraction.
Keep `temperature=0` for reproducibility.

Sources checked on 2026-06-22:

- <https://ollama.com/library/llama3.1:8b>
- <https://ollama.com/library/qwen3:8b>
- <https://ollama.com/library/qwen3.5>
- <https://ollama.com/library/gemma3>
- <https://ollama.com/library/gemma4>

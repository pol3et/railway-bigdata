# GAP-034 Silver Sentiment Encoder Research

Date: 2026-06-25

Workflow: research-orchestrator, after local file review.

Local files reviewed first:

- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/schema.py`
- `src/railway_lakehouse/gold/build.py`
- `tests/test_silver_news_extract_prompt.py`
- `tests/test_silver_news_parsers.py`
- `tests/test_silver_news_wide_contract.py`
- `docs/GAP_REGISTER.md`
- `docs/GAP_TASKS.md`
- `docs/DATA_CONTRACTS.md`
- `docs/TASKS.md`
- `docs/index.html`

Routed providers and queries:

- Context7: `Hugging Face Transformers` / "Python transformers pipeline sentiment-analysis specify model revision and CPU device=-1. How to get label and score for text using pipeline?"
- Ref: "Hugging Face Transformers pipeline sentiment-analysis device revision parameter Python documentation" (provider returned "Not enough credits"; no Ref content used).
- Tavily: "cardiffnlp/twitter-xlm-roberta-base-sentiment model card details ... current commit/revision id ... Transformers pipeline docs".
- Direct source fetches: Hugging Face model API, model `README.md`, `config.json`, Git HEAD, Transformers pipeline docs markdown, Hugging Face Hub download/cache docs, arXiv abstract page.

Sources:

- Hugging Face model card: https://huggingface.co/cardiffnlp/twitter-xlm-roberta-base-sentiment
- Hugging Face model API: https://huggingface.co/api/models/cardiffnlp/twitter-xlm-roberta-base-sentiment
- Model config: https://huggingface.co/cardiffnlp/twitter-xlm-roberta-base-sentiment/raw/main/config.json
- Pinned model revision verified by Hugging Face API and `git ls-remote`: `f2f1202b1bdeb07342385c3f807f9c07cd8f5cf8`
- XLM-T repository: https://github.com/cardiffnlp/xlm-t
- XLM-T paper / arXiv: https://arxiv.org/abs/2104.12250
- Transformers pipeline docs: https://huggingface.co/docs/transformers/en/main_classes/pipelines
- Hugging Face Hub file download/cache docs: https://huggingface.co/docs/huggingface_hub/en/package_reference/file_download

Findings:

- The originally drafted spec is stale against the live code: GAP-050 already removed `sentiment`, `language`, `operators`, and `rail_lines` from the LLM prompt/schema. GAP-034 should keep that narrowed prompt and add the deterministic sentiment post-pass.
- The model card says `cardiffnlp/twitter-xlm-roberta-base-sentiment` is a multilingual XLM-RoBERTa-base sentiment model trained on about 198M tweets and sentiment-fine-tuned on eight languages: Arabic, English, French, German, Hindi, Italian, Spanish, and Portuguese. English and German are in-domain for the fine-tune set. Hungarian is not in that fine-tune list; it is a multilingual transfer use case, not a proven HU sentiment benchmark.
- The model config maps labels as `0=negative`, `1=neutral`, `2=positive`; the pipeline returns a label plus a softmax score.
- The current model HEAD is `f2f1202b1bdeb07342385c3f807f9c07cd8f5cf8`. Use the full commit hash in code, not the stale draft prefix `59b7eda`.
- The PyTorch checkpoint is 1,112,271,561 bytes by HEAD response at the pinned revision. The draft's 268 MB claim is wrong for this model artifact.
- Transformers `pipeline(...)` accepts a `revision` parameter for branch/tag/commit pinning and a `device` parameter for placement. The docs describe `sentiment-analysis` as an alias of `text-classification`; pipeline outputs dictionaries containing label/score for text-classification.
- Hugging Face Hub downloads are cached under its normal cache layout, with snapshots keyed by commit and blob content. No model weights should be committed to this repository.

Implementation implications:

- Add `transformers>=4.40,<5` as requested, but keep imports lazy so CI and import tests do not require model weights or a backend.
- Do not add a live-model test to the default suite. Unit tests must mock the pipeline.
- Populate the existing wide fields rather than adding schema fields: `sentiment`, `confidence`, `sentiment_label`, `sentiment_confidence`, and signed `sentiment_score`.
- Update Gold to prefer `sentiment_score` when present, with `_SENTIMENT_MAP` retained for GDELT passthrough and legacy rows.

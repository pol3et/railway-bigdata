# Non-LLM NLP for news features (encoders / spaCy / Spark NLP / sentence-transformers) — 2026-06-24

Skill: `research-orchestrator`. Routed MCP providers: Tavily (search), with HuggingFace / spaCy / Spark NLP / sbert pages as primary sources.

## Question
For the HU/AT railway-news lakehouse (local Ollama qwen3.5:9b + Spark, Silver `NewsFeature` extraction),
which non-LLM NLP tools should take over which features: transformer encoders (XLM-R / FinBERT / huBERT /
German BERT / twitter-xlm-roberta-sentiment), spaCy NER, Spark NLP, and sentence-transformers
(LaBSE / MiniLM / BGE-m3)? For each: pros, cons, fit, and whether it beats the LLM on that feature.

## Local context
- `src/railway_lakehouse/silver/schema.py`: `NewsFeature` = language, is_rail_related, country, event_type
  (10-class enum), operators (closed list NER), rail_lines (free NER), monetary_amount_eur/raw, summary_en
  (translation+summarization), sentiment (neg/neu/pos), confidence.
- `silver/config.py`: NEWS_EVENT_TYPES (10), KNOWN_OPERATORS (MÁV, GYSEV, ÖBB, Westbahn, RailCargo, other).
- `docs/SILVER_DESIGN.md`: LLM used only on labels + article text; GDELT GKG themes/tone/persons/orgs used directly.
- LLM baseline: Ollama `qwen3.5:9b-q8_0` (11 GB) / q4_K_M (6.6 GB), JSON-mode, temperature 0.

## Queries run (Tavily advanced)
1. twitter-xlm-roberta-base-sentiment languages (HU/DE)
2. huBERT / NYTK Hungarian NER models
3. spaCy Hungarian support reality
4. Spark NLP pretrained pipelines / multilingual / resource needs
5. sentence-transformers LaBSE vs MiniLM vs BGE-m3 vs e5
6. German BERT sentiment + FinBERT
7. spaCy de_core_news / xx NER quality benchmarks
8. zero-shot multilingual classification (mDeBERTa / bge-m3-zeroshot)
9. language identification (fastText / lingua) on short text

## Key findings
- **twitter-xlm-roberta-base-sentiment** (cardiffnlp): XLM-R fine-tuned on ~198M tweets, sentiment tuned on 8 langs
  (incl. **De**), usable on 30+ langs incl. **Hungarian** (in pretraining corpus). 3-class neg/neu/pos = exact match
  to `NewsFeature.sentiment`. Twitter-domain bias is the main caveat for formal news.
- **FinBERT** (ProsusAI): **English-only**, financial domain (Reuters TRC2). Wrong language + wrong domain (railway
  ops/policy, not equities). Reject for this project.
- **german-sentiment-bert** (oliverguhr): German-only, very high in-domain F1 (~0.96 combined). Good DE specialist
  but monolingual.
- **huBERT** (SZTAKI-HLT/hubert-base-cc): Hungarian BERT, **NER F1 97.62%** on Szeged corpus (fine-tuned).
  **NYTK/named-entity-recognition-nerkor-hubert-hungarian**: ready NER pipeline, F1 90.18% (NerKor, PER/LOC/ORG/MISC).
- **spaCy**: no official **Hungarian** pipeline ("none yet" on spacy.io/usage/models). German `de_core_news_*` exists
  but **NER is weak** (~65% F1 on German LOC in Dagstuhl LDK2021; ~0.78 ORG / 0.86 LOC in the 2025 pilot benchmark,
  PERSON recall poor). `de_dep_news_trf` uses bert-base-german-cased and improves tagging/parsing but ships no NER.
  `xx_ent_wiki_sm` is multilingual but Wikipedia-trained, coarse (PER/LOC/ORG/MISC), low accuracy.
  **HuSpaCy** (3rd-party, `hu_core_news_trf` on huBERT) is the credible Hungarian spaCy option.
- **Spark NLP** (John Snow Labs): 18k+ models / 235+ langs incl. Hungarian, runs NER/sentiment/embeddings (incl. LaBSE)
  **natively inside Spark** via PretrainedPipeline / annotators. BUT pretrained NER/sentiment pipelines are richest in
  en/fr/de/it; needs **JVM + fat JAR + ~16 GB driver memory** even on `local[*]`, KryoSerializer config. Heavy for one
  laptop; the right tool only if "extract at Spark scale across the cluster" is the actual requirement.
- **sentence-transformers**: **LaBSE** (109 langs) = bitext/translation-pair & **dedup** specialist; sbert + AImultiple
  note it is *weaker for retrieval* (similarity-trained, coarse). **paraphrase-multilingual-MiniLM-L12-v2** (50+ langs,
  384-dim) = fast clustering. **BGE-m3** (100+ langs, 1024-dim, 8192 ctx, dense+sparse) and **multilingual-e5** = best
  for semantic search/retrieval. Map: LaBSE→dedup, e5/BGE-m3→search/RAG, MiniLM→cheap clustering.
- **Zero-shot**: `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` (100 langs) and `bge-m3-zeroshot-v2.0` (most performant
  multilingual, 0.57B) do **multilingual zero-shot** classification with no training data → fits `event_type` 10-class
  and `is_rail_related` gate. Caveat: HF advises EN-only models + machine translation can beat multilingual ones.
- **Language ID**: fastText lid.176 / lingua are cheap and accurate (lingua best on short text); the `language` field
  should never burn an LLM call.

## Recommendation (role split)
- **LLM (qwen3.5)** keep ONLY: `summary_en` (translation+abstractive summarization), `monetary_*` normalization, and
  hard semantic disambiguation / low-confidence fallbacks.
- **spaCy / HuSpaCy**: cheap reproducible linguistics (tokenize, lemma, POS, sentence split) + first-pass NER. German
  via `de_core_news_lg`; Hungarian via HuSpaCy `hu_core_news_trf`. `rail_lines` candidate generation.
- **Encoders**: sentiment via twitter-xlm-roberta-base-sentiment (multilingual) or per-lang specialists
  (german-sentiment-bert + huBERT-finetuned); `event_type` + `is_rail_related` via mDeBERTa/bge-m3 zero-shot;
  operators NER best via huBERT NerKor for HU + de_core_news/german models for DE, then dictionary-match to KNOWN_OPERATORS.
- **sentence-transformers**: LaBSE for cross-lingual **dedup** of the same story across HU/DE/EN feeds; BGE-m3 / e5 for
  semantic search + clustering Gold features; cheap, embarrassingly parallel — ideal Spark map job.
- **Spark NLP**: adopt ONLY if the course wants NER/embeddings demonstrably distributed *inside* Spark (it satisfies the
  Big Data requirement natively); otherwise run encoders/spaCy per-partition via `mapInPandas`/pandas UDF on the existing
  Spark cluster and avoid the 16 GB JVM tax.

These are deterministic, cacheable, and reproducible (vs LLM non-determinism) on every feature except free-text
summary/translation, which stays with the LLM.

## Sources
- https://huggingface.co/cardiffnlp/twitter-xlm-roberta-base-sentiment
- https://huggingface.co/cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual
- https://github.com/cardiffnlp/xlm-t
- https://github.com/ProsusAI/finBERT
- https://github.com/oliverguhr/german-sentiment
- https://hlt.bme.hu/en/resources/hubert
- https://huggingface.co/SZTAKI-HLT/hubert-base-cc
- https://huggingface.co/NYTK/named-entity-recognition-nerkor-hubert-hungarian
- https://github.com/huspacy/huspacy
- https://spacy.io/usage/models
- https://spacy.io/models/de
- https://spacy.io/models/xx
- https://drops.dagstuhl.de/storage/01oasics/oasics-vol093-ldk2021/OASIcs.LDK.2021.11/OASIcs.LDK.2021.11.pdf
- https://arxiv.org/html/2509.12098v1
- https://github.com/JohnSnowLabs/spark-nlp
- https://www.johnsnowlabs.com/spark-nlp
- https://sparknlp.org/docs/en/install
- https://www.sbert.net/docs/sentence_transformer/pretrained_models.html
- https://aimultiple.com/multilingual-embedding-models
- https://docs.ionos.com/cloud/ai/ai-model-hub/models/embedding-models/bge-m3
- https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7
- https://huggingface.co/collections/MoritzLaurer/zeroshot-classifiers
- https://medium.com/besedo-engineering/language-identification-for-very-short-texts-a-review-c9f2756773ad

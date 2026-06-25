# Local LLM role for structured feature extraction in the railway-news lakehouse

> Skill: research-orchestrator (forced search before answering)
> Routed MCP providers: mcp__tavily__tavily_search, mcp__exa__web_search_exa
> Date: 2026-06-24

## Scope
Whether/where a LOCAL LLM (repo currently runs Ollama + `qwen3.5:9b-q8_0`, JSON mode,
`temperature=0`, `think=false`, `num_ctx=8192`, `num_predict=1024`) belongs in a HU/DE/EN
railway-news feature pipeline at lakehouse scale; model choice; reproducibility/throughput;
how to call it from Spark.

## Queries run
- "best local LLM 2025 multilingual structured JSON extraction Qwen2.5 vs Gemma vs Llama German Hungarian"
- "LLM vs spaCy vs BERT NER sentiment when to use which feature extraction pipeline reproducibility cost"
- "calling LLM from Spark pandas UDF batch inference external service best practice 2025 throughput"
- "Ollama structured outputs JSON schema enforcement reproducibility determinism temperature 0 thousands of documents throughput batching"
- "GLiNER multilingual NER Hungarian German huSpaCy XLM-RoBERTa sentiment classification local reproducible"
- "LLM event extraction typing from news ... sentiment at scale reliability calibration self-reported confidence unreliable"

## Key findings
- Repo already scopes the LLM correctly: only the HU/DE column crosswalk + per-article news
  features; "We never push numeric table rows through it" (`silver/ollama_client.py`).
- Model choice: Qwen2.5/Qwen3 family is the consensus multilingual pick (Apache-2.0,
  100+ langs incl. HU/DE); Gemma 3/4 best RAM/throughput; Mistral Small strong on DE.
  7-9B at Q4/Q8 is the right size band for single-box extraction.
- Structured outputs: Ollama >=0.5 `format` field enforces a JSON schema (grammar-constrained),
  more reliable than bare `format:"json"`. Repo uses this. Keep schema nesting <3 levels.
- Determinism caveat: `temperature=0` is greedy but NOT byte-stable across the FIRST call
  after model load and across Ollama/driver versions (ollama issue #16197). So pin model
  digest + version, persist the Silver output, and treat the LLM pass as a cached one-time job.
- Where LLM should NOT be used: sentiment at scale (self-reported confidence is uncalibrated /
  overconfident, run-to-run variance) -> use a fine-tuned XLM-R/BERT classifier; high-volume
  deterministic NER -> spaCy / huSpaCy / GLiNER are cheaper, reproducible, faster; anything
  numeric -> deterministic parsing, never the LLM.
- Spark calling pattern: do NOT call an LLM row-by-row inside a Python UDF in the hot path.
  Use `predict_batch_udf` (Spark 3.4+/4.0) against an external serving endpoint (vLLM/Triton/
  Ollama) OR — preferred here — run a ONE-TIME batched Silver pass outside Spark, write Parquet,
  let Spark/Gold read deterministic columns. NVIDIA + Databricks both push the external-service
  + batch-inference pattern, not in-executor model loading.
- Throughput: Ollama parallelism is limited; multi-GPU needs N independent servers + a load
  balancer (robert-mcdermott ollama-batch-cluster). vLLM/SGLang far higher throughput if needed.

## Sources
- https://computingforgeeks.com/open-source-llm-comparison
- https://www.siliconflow.com/articles/en/best-open-source-LLM-for-German
- https://docs.ollama.com/capabilities/structured-outputs
- https://ollama.com/blog/structured-outputs
- https://github.com/ollama/ollama/issues/16197
- https://developer.nvidia.com/blog/accelerate-deep-learning-and-llm-inference-with-apache-spark-in-the-cloud
- https://community.databricks.com/t5/technical-blog/apache-spark-4-0-a-new-era-for-scalable-machine-learning-and-ai/ba-p/120627
- https://github.com/robert-mcdermott/ollama-batch-cluster
- https://github.com/huspacy/huspacy
- https://stackoverflow.com/questions/78895710/ner-versus-llm-to-extract-name-gender-role-and-company-from-text
- https://arxiv.org/html/2509.12098v1
- https://pmc.ncbi.nlm.nih.gov/articles/PMC12375657/
- https://callsphere.ai/blog/classification-structured-outputs-sentiment-intent-category-detection.md

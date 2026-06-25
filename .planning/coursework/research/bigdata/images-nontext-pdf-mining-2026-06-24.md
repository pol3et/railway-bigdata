# Should the railway-news lakehouse process IMAGES / non-text?

> Skill: research-orchestrator | Routed MCP providers: Tavily (tavily_search), Exa (web_search_exa), WebFetch
> Date: 2026-06-24 | Task slug: images-nontext-pdf-mining

## Queries run
- Tavily: "PDF table extraction Python comparison pdfplumber camelot tabula docling unstructured accuracy"
- Tavily: "value of image analysis in news media monitoring pipeline CLIP embeddings captioning object detection worth it"
- Tavily: "Docling IBM PDF document extraction tables figures OCR scanned vs born-digital VLM pipeline 2025"
- Tavily: "UIC railway statistics synopsis PDF born-digital text layer vector charts tables 2025"
- Tavily: "multimodal pipeline complexity cost vs text-only NLP ROI when not to add computer vision data engineering"
- Exa: "Qwen2.5-VL vs Llava local vision language model Ollama document understanding OCR PDF tables benchmark 2025"
- Exa: "do news article lead images add analytical value vs effort image deduplication CLIP scene detection diminishing returns"
- Exa: "spaCy multilingual NER German Hungarian news vs LLM extraction lightweight"
- WebFetch: NVIDIA "Approaches to PDF Data Extraction for Information Retrieval"

## Key findings

### 1. News images add marginal analytical value, high effort
- News-image work in the literature is almost entirely *retrieval / editorial* (matching an image to an article, thumbnail representativeness, fake-news thumbnail incongruity) — NOT producing numeric analytic features. MediaEval 2023/2025 NewsImages papers report best similarity ~0.42 and that adding article lead text to CLIP gave "very small" gains "perhaps not worth the extra time and computing power."
- CLIP image-text incongruity *can* flag misinformation thumbnails, but that is a research task, not a HU/AT rail-stats deliverable.
- Lead images on rail news are mostly stock photos of trains/stations → near-zero discriminative signal for HU/AT rail trend analysis.

### 2. PDF extraction — the one real non-text win (UIC PDFs)
- UIC source (`bronze/sources/uic.py`) lands "Railway Statistics Synopsis" + "Traffic Trends" PDFs as raw bytes. These are born-digital publication PDFs (text layer + tables), not scans.
- Tool accuracy (Medium 12-tool test / arXiv 2410.09871): TableFormer/Docling ~93.6% avg table accuracy vs Tabula 67.9%, Camelot 73.0%. Camelot only works on text-based (non-scanned) PDFs. pdfplumber gives pixel-level control + visual debugging, strongest for ambiguous layouts, pure-Python.
- Docling (IBM, Apache-2.0, local): PDF→Markdown/JSON, layout + reading order + TableFormer table structure, runs locally on CPU (~2-6s/table). Has both a classic model pipeline and an optional VLM (Granite-Docling-258M).
- VLM-for-PDF is the wrong default: NVIDIA benchmark — OCR pipeline 8.47 pages/s vs VLM 0.26 pages/s (**32.3x slower**), VLM 7.2% worse retrieval accuracy, and VLMs hallucinate chart titles / misread axes / drop table rows. Reddit/RAG consensus: extract text from the PDF text layer, only send detected table/chart *regions* to a VLM if needed.

### 3. Local vision-LLM options (if pursued)
- Qwen2.5-VL 7B (ollama `qwen2.5vl:7b`) is the clear local leader: DocVQA 95.7, OCRBench 86.4, ChartQA 87.3; structured JSON from invoices/forms/tables; multilingual OCR incl. German. Outperforms Llama-3.2-Vision 11B and beats Llama-3.2-90B on DocVQA. LLaVA is now legacy/outperformed.
- PaddleOCR-VL 0.9B runs on CPU, OmniDocBench 92.6 — specialist for layout/table fidelity.
- Cost: adds a *second* large model alongside the existing text `qwen3.5:9b`; VRAM pressure on a local box, 32x slower throughput than deterministic parsers.

### 4. Multilingual text is where the marginal effort should go (HU/DE/EN)
- HuSpaCy `hu_core_news_lg` (CPU, CNN, pretrained vectors) gives Hungarian tokenize/lemma/POS/NER; `de_core_news_lg` for German — both newswire-genre, CPU-friendly.
- spaCy-vs-LLM (Markaicode 2026): spaCy NER runs in ms/doc, deterministic, cheap; LLMs are 7-30x slower. Recommended pattern = fast spaCy/encoder for standard entities (ORG/GPE/operators/lines) + LLM fallback for ambiguous/novel extraction. This is the existing NewsFeature LLM path, complemented not replaced.

## Decision (recorded)
Text + stats is sufficient. The ONLY non-text win worth doing is **PDF table/text extraction of the already-landed UIC stats PDFs** (Silver concern, per `uic.py` docstring), using deterministic born-digital parsers (pdfplumber/Camelot or Docling classic), feeding numeric StatFacts. Skip image captioning/CLIP/object-detection/scene-detection — marginal analytic value, high pipeline + maintenance cost, off-topic for depth/volume scoring. Skip vision-LLM-as-default-PDF-parser (32x slower, hallucination risk); keep a VLM only as an optional last-resort fallback for chart-only pages. Spend any extra "depth" budget on multilingual HU/DE text features (HuSpaCy + de_core_news + existing LLM extraction) — that directly increases feature volume on the project's actual subject.

## Sources
- https://arxiv.org/html/2410.09871v1 (PDF parser comparison)
- https://medium.com/@kramermark/i-tested-12-best-in-class-pdf-table-extraction-tools-and-the-results-were-appalling-f8a9991d972e
- https://camelot-py.readthedocs.io (Camelot text-based-only limitation)
- https://arxiv.org/html/2408.09869v5 (Docling Technical Report)
- https://heidloff.net/article/docling (Docling classic vs VLM)
- https://developer.nvidia.com/blog/approaches-to-pdf-data-extraction-for-information-retrieval (OCR vs VLM 32.3x)
- https://ollama.com/library/qwen2.5vl
- https://insiderllm.com/guides/vision-models-locally/ (VLM benchmark table)
- https://arxiv.org/abs/2502.13923 (Qwen2.5-VL Technical Report)
- https://2025.multimediaeval.com/paper16.pdf (lead text marginal gain)
- https://arxiv.org/html/2402.11159v3 (news thumbnail representativeness / CLIP)
- https://aclanthology.org/2022.constraint-1.10.pdf (CLIP fake-news thumbnail incongruity)
- https://markaicode.com/vs/spacy-vs-transformers-vs-llm-ner-production/
- https://huspacy.github.io/models/index_trf_xl/ and https://spacy.io/models/de
- https://uic.org/support-activities/statistics (UIC Synopsis publications)

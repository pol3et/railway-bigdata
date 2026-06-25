# GAP-043 News Evaluation Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build only the Option C deterministic news/model evaluation harness, with synthetic seed data and no live model, fetch, or labeling work.

**Architecture:** Add a pure `railway_lakehouse.eval.news` metrics module and a small `railway_lakehouse.eval.harness` runner that loads a parameterized golden corpus plus predictions, aligns by `article_id`, computes TEST-partition metrics with fixed-seed bootstrap CIs, applies min-support demotion and CI-overlap regression checks, then writes deterministic report artifacts under `output/evidence/news_eval/`. Tests drive the public API with synthetic `tmp_path` corpora and mocked prediction JSON.

**Tech Stack:** Python 3.12+, stdlib, NumPy, pandas, pyarrow for optional parquet input; no sklearn/scipy/rouge hard dependency.

## Global Constraints

- Build the harness only; no Option A re-extraction, no article fetching, no live Ollama/XLM-R/lid, and no labeling.
- Raw Bronze remains immutable; this task does not touch Bronze ingestion.
- Numeric stats merging stays deterministic; this task does not touch stats merge code.
- Runtime outputs go under `output/`.
- Tests must not depend on `coursework/` data; use `tmp_path` and committed synthetic fixtures only.
- Golden corpus path is a parameter, never hardcoded to the current 40-row sample.
- Current real data limitation must be recorded: committed Silver has no title/body and the raw Bronze title/body sample is absent/gitignored, so real label quality is gated on a future owner-approved bounded re-extraction.
- Default gates use min support `n >= 30`; unsupported cells demote to report-only.
- Primary regression gate uses bootstrap 95% CI overlap, not a raw fixed delta.
- Dashboard/docs sync is required because this advances GAP-043 state.

---

### Task 1: Red Tests For Harness Contract

**Files:**
- Create: `tests/test_news_eval_harness.py`

**Interfaces:**
- Consumes planned functions `run_evaluation(...)`, `main(argv)`, `cohens_kappa(...)`.
- Produces failing coverage for perfect/degraded/support/partition/baseline/digest/determinism/CLI behavior.

- [x] Write tests with synthetic rows in `tmp_path`, including `partition`, `*_gold` fields, duplicate groups, money, language, sentiment, operators, and rail lines.
- [x] Run `python -m pytest -q tests/test_news_eval_harness.py`.
- [x] Confirm the failure is caused by missing `railway_lakehouse.eval` modules, not fixture errors.

### Task 2: Metric Primitives

**Files:**
- Create: `src/railway_lakehouse/eval/__init__.py`
- Create: `src/railway_lakehouse/eval/news.py`

**Interfaces:**
- Produces constants/functions from the spec: `EVENT_SUPERCLASS`, `to_superclass`, `accuracy`, `precision_recall_f1`, `macro_f1`, `confusion_matrix`, `set_micro_prf`, `monetary_match_rate`, `bcubed_prf`, `geoyear_count_error`, `cohens_kappa`, `bootstrap_ci`, `ci_overlap`, `compute_all_metrics`.

- [x] Implement pure NumPy/pandas helpers with explicit dict-key reads and sorted label/key ordering.
- [x] Implement fixed-seed row bootstrap over contributing row indices.
- [x] Implement min-support demotion and report-only reasons for HU sentiment, NER, rail lines, monetary, B-cubed, optional ROUGE, and calibration diagnostics.
- [x] Run `python -m pytest -q tests/test_news_eval_harness.py` and iterate until metric-level tests pass.

### Task 3: Harness Runner And CLI

**Files:**
- Create: `src/railway_lakehouse/eval/harness.py`

**Interfaces:**
- Produces `run_evaluation(golden_set_path, extraction_results_path, *, model_digest=None, metric_thresholds=None, baseline_path=None, partition="TEST", min_support=30, boot_seed=12345, out_dir="output/evidence/news_eval/") -> dict`.
- Produces `main(argv=None) -> int` with flags `--golden-set`, `--extraction-results`, `--model-digest`, `--out`, `--metric-thresholds`, `--baseline`, `--partition`, `--min-support`, `--boot-seed`.

- [x] Implement JSON/parquet loading, article alignment, partition filtering, sidecar manifest detection for digest bundle when available, and deterministic JSON writers.
- [x] Implement absolute-threshold violations only for gated metrics and non-regression violations only when baseline exists and CIs do not overlap below baseline.
- [x] Write `manifest.json`, `metric_summary.json`, and `per_article_scores.csv`.
- [x] Run `python -m pytest -q tests/test_news_eval_harness.py` until the focused harness suite is green.

### Task 4: Synthetic Fixture And Protocol Docs

**Files:**
- Create: `tests/fixtures/news_golden_set.json`
- Create: `tests/fixtures/news_golden_set.README.md`
- Create: `tests/fixtures/news_golden_baseline.json`
- Create: `docs/GOLDEN_SET_PROTOCOL.md`

**Interfaces:**
- The fixture is clearly labeled synthetic seed data and is not used as a real labeled corpus claim.
- The protocol records the future Sonnet-labeling rubric and data-availability blocker.

- [x] Add a small synthetic placeholder golden set with TUNE/TEST rows and explicit metadata note fields.
- [x] Add a synthetic baseline fixture for deterministic non-regression tests.
- [x] Add `docs/GOLDEN_SET_PROTOCOL.md` from the directive’s requirements, noting the referenced orchestrator artifact was missing in this checkout.
- [x] Keep the real corpus path parameterized in every example.

### Task 5: Research, Dashboard, And Verification Docs

**Files:**
- Create/update: `.planning/coursework/research/bigdata/news-eval-harness.md`
- Modify: `docs/GAP_REGISTER.md`
- Modify: `docs/TASKS.md`
- Modify: `docs/index.html`
- Modify: `docs/VERIFICATION.md`
- Modify: `docs/PROGRESS_LOG.md`
- Modify: `.planning/COURSEWORK_PROGRESS.md`

**Interfaces:**
- Research record names `research-orchestrator`, local-first findings, Ref credit block, Context7/Tavily sources, and source URLs.
- Docs close or advance GAP-043 only for harness/protocol/synthetic fixture, not real golden labels.

- [x] Record local and external research sources.
- [x] Update GAP-043 row and test failure mapping with focused and full verification commands after executing them.
- [x] Update dashboard/task copy to state the harness is implemented while real label quality remains blocked on Option A.
- [x] Append handoff entries with exact files and executed commands.

### Task 6: Final Verification And PR

**Files:**
- No new implementation files unless verification exposes a defect.

**Commands:**
- `python -m pytest -q tests/test_news_eval_harness.py`
- `python -m pytest -q`
- `python -m compileall -q src tests`
- `python -c "import railway_lakehouse.eval.harness; import railway_lakehouse.eval.news"`
- `git diff --check`

- [x] Run all required commands and record actual outputs before claiming success.
- [x] Commit the scoped changes on `impl/gap-043`.
- [x] Push to origin and open a PR against `main`.
- [x] Verify the PR is mergeable.

## Self-Review And Approval

Spec coverage:
- The plan covers Option C harness-only scope, metric primitives, CLI, deterministic mocked tests, synthetic fixture, model digest manifest, CI-overlap non-regression, min-support demotion, TUNE/TEST partitioning, protocol docs, dashboard sync, research record, verification, commit, push, and PR.
- The plan explicitly excludes live extraction, article fetching, live models, and labeling.

Stale/thin spec refinements:
- `output/evidence/orch/gap-043/GOLDEN_SET_PROTOCOL.md` is missing in this checkout, so `docs/GOLDEN_SET_PROTOCOL.md` must be reconstructed from the directive and existing `docs/SPEC_NEWS_PREPROCESSING.md` / `docs/GAP_TASKS.md`.
- The old `docs/GAP_TASKS.md` GAP-043 text expects 100+ real labeled rows and optional pipeline integration; the user directive supersedes it with a small synthetic placeholder fixture and no pipeline integration in this PR.
- The live `NewsFeature` contract has 44 fields including `is_duplicate`, not the older 15-field text in the stale GAP-043 draft.

Approval:
- Approved for implementation as written, scoped to GAP-043 only.

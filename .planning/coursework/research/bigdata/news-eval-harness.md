# GAP-043 News Evaluation Harness Research

Date: 2026-06-25

Skills/workflow:
- Used `research-orchestrator` as required by `AGENTS.md`.
- Used `$ship-it` delivery discipline with a repo-local plan and no Linear.
- Local files were researched first.

## Local Findings

- `src/railway_lakehouse/silver/schema.py` defines a 44-field `NewsFeature`
  dataclass; the current persisted feature rows do not include original article
  `title` or `body`.
- `output/evidence/news-extraction-sample/silver/news/news_feature/ingest_date=2026-06-25/news_feature.parquet`
  is the committed GAP-033 sample. The accompanying `MANIFEST.md` records 40
  real rows, but the labelable raw Bronze article text is ignored and absent
  from this checkout.
- `.gitignore` ignores `output/evidence/**/bronze/`, matching the
  data-availability blocker in the GAP-043 directive.
- `docs/GAP_REGISTER.md` still had GAP-043 open before this change; dashboard
  sync is required because this PR touches `src/railway_lakehouse/**` and
  advances the gap state.
- `output/evidence/orch/gap-043/GOLDEN_SET_PROTOCOL.md` was referenced by the
  directive but is not present in this checkout, so `docs/GOLDEN_SET_PROTOCOL.md`
  was reconstructed from the directive and existing project specs.

## External Sources

Ref MCP was attempted for metric/API definitions but returned "Not enough
credits"; routing continued through Context7 and Tavily.

- NumPy random/percentile docs via Context7:
  - https://numpy.org/doc/2.4/reference/random/index.html
  - https://numpy.org/doc/2.4/reference/generated/numpy.percentile.html
  - Used for fixed `default_rng(seed)` reproducibility and percentile CI bounds.
- pandas IO docs via Context7:
  - https://pandas.pydata.org/docs/reference/api/pandas.read_parquet.html
  - https://pandas.pydata.org/docs/user_guide/io.html
  - Used for JSON/parquet/CSV report IO behavior.
- scikit-learn metric docs via Context7:
  - https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html
  - https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html
  - Used only as metric-definition reference; sklearn is not a dependency.
- Cohen's kappa source via Tavily:
  - https://pmc.ncbi.nlm.nih.gov/articles/PMC3900052/
  - Used for the observed-minus-expected-over-one-minus-expected formula.
- B-cubed clustering metric sources via Tavily:
  - https://link.springer.com/article/10.1007/s10791-024-09436-7
  - https://irlab.science.uva.nl/wp-content/papercite-data/pdf/van-2022-bcubed.pdf
  - Used for per-element cluster precision/recall averaged over elements.
- Bootstrap percentile CI sources via Tavily:
  - https://www.amstat.org/docs/default-source/amstat-documents/edu-resamplingundergradcurriculum.pdf
  - http://library.virginia.edu/data/articles/bootstrap-estimates-of-confidence-intervals
  - Used for resampling with replacement and percentile confidence intervals.

## Spec Refinements

- The stale `docs/GAP_TASKS.md` GAP-043 text expects a 100+ real labeled corpus.
  The user directive supersedes that for this PR: ship the harness and a small
  synthetic placeholder only; real labeling is gated on a future owner decision.
- Optional pipeline integration and `golden_set_builder.py` are not needed for
  the Option C harness-only scope.
- The harness must record the data-availability blocker and the silver-standard
  caveat in committed docs/manifests.

## Implementation Notes

- Metrics are implemented in `src/railway_lakehouse/eval/news.py` without
  sklearn/scipy/rouge hard dependencies.
- `run_evaluation(...)` accepts a parameterized golden-set path, JSON/parquet
  prediction inputs, optional threshold overrides, optional baseline, partition,
  min support, and bootstrap seed.
- The deterministic CI harness uses fixed manifest timestamps so repeated runs
  with identical inputs and seed produce byte-identical manifests.

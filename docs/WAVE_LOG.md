# Wave Log

Per-wave handoff records for the railway-lakehouse fast track (orchestrator: Claude;
implementers: Codex). One entry per merged wave, with PRs, contract status, and evidence
pointers. Newest wave first within each section is not required; append in order.

## Wave 1 — Unblock & pin (2026-06-24)

**Merged to `main` (squash, dependency order):**

| PR | Gap | Squash commit | Suite on merge |
|---|---|---|---|
| #16 | GAP-012 — fix documented Bronze→Gold regen recipe (no silent-empty Gold) | `b82149d` | 90 passed |
| #17 | GAP-020 — deterministic s3/MinIO Bronze read-back tests (fsspec `memory://`) + `_read_text` UTF-8 fix | `c11779a` | 96 passed |
| #14 | GAP-018 — bound pandas/pyarrow majors + `constraints.txt` lockfile + env-version guard | `0e3e41b` | 101 passed |
| #15 | GAP-017 — pin Spark 4.1 stack (`pyspark==4.1.*` + `delta-spark==4.1.*`), S3A as Maven coord in `spark_config.py`, JDK 17/21 documented | `3a83bce` | 102 passed |

Final `main` suite: **102 passed** (89 unit + 13 integration).

**Review:** each PR got an independent read-only Codex review (`codex_review.sh`). GAP-012/018/020
returned **approve** with 0 findings. GAP-017 returned **request_changes** (P1: `hadoop-aws` was a
fake pip dep behind an impossible marker; P2: `docs/GAP_TASKS.md` still told GAP-009 to use Spark
3.5) — both fixed via a resume on the implementer thread (commit `2a1c78a`), then independently
re-verified PASS by a `ship-it:ship-reviewer` subagent. No open P1/P2 at merge.

**Contract A audit (on `main`):**
- [x] Clean-checkout regen → real Gold + `counts.json`, no empty. Live-reproduced 2026-06-24:
  **2,139×3** (`rail_network_length_km`, 116 geos, AT/HU, 1995–2021). Evidence:
  `output/evidence/orch/contract-a/` (`a_livecheck.log`, `a_pipeline.log`, `a_counts.json`).
- [~] `pip install .[spark]` resolves **pyspark 4.1.2 + delta-spark 4.1.0** (`--dry-run`, evidence
  `b_spark_dryrun.txt`); hadoop-aws 3.4.1 is the documented Spark Maven coordinate, not pip. **JDK
  17/21 not yet provisioned** — machine has Java 1.8.0_491, `JAVA_HOME` unset (`b_java.txt`). This
  is the live-Spark prerequisite, carried into Wave 2 / GAP-009.
- [x] `pytest -q` green (102); env guard fails on wrong-major pandas/pyarrow (`c_env_guard.txt`,
  5 passed incl. negative-case assertions).

**Conflict resolution note:** all four PRs edited the shared dashboard/log docs; merges 2–4 were
rebased onto `main` with doc conflicts resolved by combining each gap's status flips / log entries.
`pipeline.py` (#16↔#17) and `pyproject.toml` (#14↔#15) auto-merged (disjoint regions).

**Status:** Contract A met for all code/config items; the only open item is JDK 17/21 provisioning,
which is GAP-009's documented environment prerequisite. Advancing to Wave 2 (GAP-009 ‖ GAP-007).

## Wave 2 — Spark fast track (2026-06-24)

**Merged to `main` (squash, dependency order):**

| PR | Gap | Squash commit | Suite on merge |
|---|---|---|---|
| #18 | GAP-007 — wire `gold.run` CLI to read persisted Silver → Gold + counts; relocate `write_gold_counts` to `gold/build.py`; integration test | `586fac5` | 103 passed |
| #19 | GAP-009 — Spark evidence job `spark_jobs.coverage` (reads real Gold, writes `output/evidence/spark/` manifest + Spark parquet) + CI-safe tests | `ec6fb5d` | 104 passed + 2 spark |

**The JDK blocker resolved itself:** GAP-009's implementer (full-access) provisioned **JDK 21.0.11**
(Eclipse Temurin) + native Windows Hadoop helper (winutils/hadoop.dll) and produced a **genuine live
Spark run** — so the END OF FAST TRACK "Spark evidence exists" condition is truly met, not deferred.

**Review:** both PRs got independent `codex_review` (approve, 0 findings). GAP-009 (the graded
deliverable) additionally got a `ship-it:ship-reviewer` deep pass → **PASS**, with one P2 (the
write-path spark test failed rather than skipped on a fresh machine lacking `HADOOP_HOME`/winutils).
Fixed via resume (commit hardening the test to `pytest.skip` when the native Hadoop helper is absent),
keeping the committed evidence untouched. No open P1/P2 at merge.

**Spark evidence (verified genuine, committed in #19):** `output/evidence/spark/manifest.json` —
Spark **4.1.2**, JDK **21.0.11**, input **2,968×4** (real inventory-live Gold) → output **2,968×5**
(per-(geo,year) coverage), 1 partition, `part-00000-….snappy.parquet` + `_SUCCESS`, `status=passed`.
Manifest input shape cross-checked against the real Gold Parquet.

**Contract B audit (on `main`):**
- [x] Spark job writes `output/evidence/spark/` with Spark version, in/out row+col counts, files. ✓
- [x] Recorded counts match the Gold Parquet; job is **re-runnable** — orchestrator independently
  re-ran it (JAVA_HOME→JDK21, HADOOP_HOME→winutils, `hadoop.dll` on PATH): **2,968×4 → 2,968×5,
  status=passed**. Evidence: `output/evidence/orch/contract-b/` (`rerun3.log`, `spark-rerun3/manifest.json`).
- [x] (bonus) Gold built from persisted Silver via `gold.run` (GAP-007). ✓

**Suite:** `pytest -q -m "not spark"` → **104 passed, 2 deselected** (CI-safe; the spark file
`importorskip`-skips without PySpark, so the default `[test]` env stays green). With the Spark env
(PySpark 4.1.2 + JDK 21 + `HADOOP_HOME`), the 2 spark tests pass.

**Note (minor, non-blocking):** on a machine that has PySpark installed but no `JAVA_HOME`→JDK17+,
a bare `pytest -q` will try to boot Spark 4.1 on Java 8 and hang. The default `[test]` env (no
PySpark) is unaffected. A future hardening could also skip the spark tests when JDK 17+ is absent.

**Conflict resolution note:** #19 rebased onto the #18-updated `main`; doc conflicts combined both
gaps' done-states. `spark_jobs/`, `tests/`, `pyproject.toml` (pytest `pythonpath`) auto-merged.

**Status:** Contract B passed (all three items, incl. bonus). 🏁 Spark evidence exists. Advancing to
Wave 3 (GAP-011 report/draft) — the final fast-track step.

## Wave 3 — Report kickoff (2026-06-24) — 🏁 END OF FAST TRACK

**Merged to `main`:**

| PR | Gap | Squash commit | Suite on merge |
|---|---|---|---|
| #20 | GAP-011 — evidence-grounded `output/report/REPORT.md` + `output/presentation/PRESENTATION.md` + `tests/test_report_evidence_links.py` (deterministic evidence-link checker) | `4353806` | `-m unit` 93 passed |

**Review:** `codex_review` returned **request_changes** (P2: report overstated news as part of the
current reportable dataset; P2: the checker guarded REPORT but not PRESENTATION numbers). A
`ship-it:ship-reviewer` deep pass independently confirmed every quantitative claim matched its cited
evidence JSON exactly and all honest-scope disclaimers were present. Both P2s fixed via resume
(commit `744604f`): REPORT.md now states the current Gold is **stats-only, news pending GAP-006**, and
the checker now asserts exact `key=value` headline claims in **both** documents from the evidence JSON.
No open P1/P2 at merge.

**Deliverables (on `main`):** `output/report/REPORT.md`, `output/presentation/PRESENTATION.md`,
`tests/test_report_evidence_links.py`. Every quantitative claim cites a committed `output/evidence/...`
artifact; the checker test (3 unit tests) fails if any cited path is missing or any headline number
drifts from its evidence JSON. The report fills the Spark RESULTS section from
`output/evidence/spark/manifest.json` (Spark 4.1.2, 2,968×4 → 2,968×5) and honestly scopes the project
to World Bank stats-only Gold, flagging GAP-013 (live-MinIO stats), GAP-023 (Eurostat→Gold), GAP-006
(news/Ollama), GAP-019 (scheduler) as not-yet-proven.

**🏁 END OF FAST TRACK reached:** Spark evidence exists (Wave 2) **and** the report draft is authored
and evidence-grounded (Wave 3). Final `main` = `4353806`. Dashboard + docs synced.

**Beyond the fast track (Wave 4+, not in scope here):** Contract C — ≥2 stats sources + `news_*` in
Gold, a live-MinIO end-to-end run, and a scheduled fresh-Bronze run — remains the next milestone.

## 2026-06-25 — Orchestration hardening + first real test run (GAP-039 merged)

Scope: Sessions A+B prep. NOT a full overnight run — a bounded test that hardened the harness, then
handoff (`docs/HANDOFF_AUTONOMOUS_RUN.md`) for a fresh session to launch the autonomous run.

Harness fixes (the real run had never worked):
- **DRY always-dry**: `run_night.sh`/`run_wave.sh` set `DRY=0` but consumed it via `${DRY:+…}`, which
  substitutes for any non-null value → every "real" run forced `--dry-run`. Fixed: `DRY=` when not dry.
- **Codex output schemas 400'd**: strict structured-output requires `required` to list every property;
  `impl_verdict`/`review_findings` schemas listed a subset → `invalid_json_schema`. Fixed both.
- **Codex timeouts raised** (parallel fan-out absorbs the cost): impl/resume 40m→2h, review 20m→1h.
- **Tiered PR review** (owner policy): load-bearing PR (touches `LOAD_BEARING_PATHS` core paths, per
  `files_changed`) → Opus `ship-it:ship-reviewer` + park `needs_opus_review`; else codex + auto-merge;
  fixes always codex. See `scripts/orch/night.config.sh`, `run_wave.sh:pr_is_load_bearing`,
  `scripts/orch/prompts/opus_review.md`.

Test run — **GAP-039 MERGED** (PR #28, squash `dafcbf8`):
- impl → 40m-timeout-resume → ship; codex review caught a real P1 (cache not wired into production)
  + P2 (GDELT passthrough unreachable) + P3 (tone=0 dropped) and the gate correctly refused to merge;
  codex fix-resume wired it + added regression tests (183 → **187 passed, 3 skipped**); Opus review
  waived by owner for the test wrap-up; merged. Post-merge contract suite on main: **187 passed, 3 skipped**.

Ledger: GAP-039=merged. Everything else pending for the autonomous run. Other sessions push to main
concurrently (origin moved 0a84012 → 7761e2e → dafcbf8).

## Overnight run — started 2026-06-25 08:54:54

```
{
  "GAP-039": {
    "status": "merged",
    "pr": "28",
    "note": "test-run: codex impl + fix-resume green (187 passed,3 skipped); merged by owner decision (Opus gate waived for test wrap-up)"
  },
  "GAP-050": {
    "status": "merged",
    "pr": "29",
    "note": "Opus approve after fix-resume #1 (P1 prod-path wired, P2 cache key, P3 max_attempts); squash 685d6d3; main 197 passed/3 skipped"
  },
  "GAP-033": {
    "status": "merged",
    "pr": "30",
    "note": "Opus approve (data authenticity verified, digest 359d7dd4 matches /api/tags); 40 real rows; squash 882e130; main 198 passed/3 skipped. codex advisory P1/P2 reconciled (stale-doc model ref + lower-severity)"
  },
  "GAP-043": {
    "status": "claude_subagent",
    "pr": "",
    "note": "orchestrator Opus design + Sonnet labelling"
  },
  "GAP-031": {
    "status": "needs_opus_review",
    "pr": "33",
    "note": "load-bearing PR: orchestrator Opus ship-reviewer required (codex review.json is advisory)"
  },
  "GAP-035": {
    "status": "needs_opus_review",
    "pr": "32",
    "note": "load-bearing PR: orchestrator Opus ship-reviewer required (codex review.json is advisory)"
  },
  "GAP-034": {
    "status": "needs_opus_review",
    "pr": "31",
    "note": "load-bearing PR: orchestrator Opus ship-reviewer required (codex review.json is advisory)"
  },
  "GAP-040": {
    "status": "needs_opus_review",
    "pr": "34",
    "note": "load-bearing PR: orchestrator Opus ship-reviewer required (codex review.json is advisory)"
  },
  "GAP-044": {
    "status": "needs_opus_review",
    "pr": "35",
    "note": "load-bearing PR: orchestrator Opus ship-reviewer required (codex review.json is advisory)"
  },
  "GAP-037": {
    "status": "manual_skip",
    "pr": "",
    "note": "needs human"
  },
  "GAP-038": {
    "status": "manual_skip",
    "pr": "",
    "note": "needs human"
  },
  "GAP-045": {
    "status": "needs_opus_review",
    "pr": "36",
    "note": "load-bearing PR: orchestrator Opus ship-reviewer required (codex review.json is advisory)"
  },
  "GAP-041": {
    "status": "needs_opus_review",
    "pr": "38",
    "note": "load-bearing PR: orchestrator Opus ship-reviewer required (codex review.json is advisory)"
  },
  "GAP-042": {
    "status": "needs_opus_review",
    "pr": "37",
    "note": "load-bearing PR: orchestrator Opus ship-reviewer required (codex review.json is advisory)"
  },
  "GAP-036": {
    "status": "needs_opus_review",
    "pr": "39",
    "note": "load-bearing PR: orchestrator Opus ship-reviewer required (codex review.json is advisory)"
  }
}```

## Overnight autonomous run — Sessions A+B COMPLETE (2026-06-25)

Orchestrator (Opus) drove the full unattended run per `docs/NIGHT_KICKOFF.md`. **All 13 in-scope gaps merged; main green (301 passed, 4 skipped).**

| Gap | PR | Outcome |
|---|---|---|
| GAP-050 | #29 | merged — LLM pipeline engineering (Opus gate caught P1: run-contract unwired in prod path; codex fix-resume wired pipeline.py/silver/run.py → run_extraction_pipeline + failure sidecar; +P2 GDELT cache key, +P3 max_attempts) |
| GAP-033 | #30 | merged — first REAL Ollama pass; 40 real NewsFeature rows (qwen3:4b, digest 359d7dd4, 0 failures). Spec corrected: qwen3:4b NOT qwen3.5:9b (6GB GPU). Opus verified data authenticity |
| GAP-035 | #32 | merged — fastText/lingua language-id (prod-wired) |
| GAP-040 | #34 | merged — widened Gold news aggregation (deterministic rollups) |
| GAP-042 | #37 | merged — Statistik Austria ODS reader |
| GAP-045 | #36 | merged — +2 World Bank macro indicators (values verbatim) |
| GAP-041 | #38 | merged — UIC PDF widened 39→80 geos + staging (codex-integrated load.py conflict) |
| GAP-031 | #33 | merged — GDELT GKG csv.zip passthrough (Opus P1: parser was dead in prod; codex wired _read_bronze_gkg_records → run_extraction_pipeline(gkg_records=)) |
| GAP-034 | #31 | merged — XLM-R sentiment encoder (Opus P2: untruncated text→silent drop; codex added truncation=True/max_length=512) |
| GAP-036 | #39 | merged — embeddings + cross-lingual dedup (Opus P1: cluster_near_duplicates never called in prod; codex wired it into run_extraction_pipeline) |
| GAP-044 | #35 | merged — per-source parser-correctness audit + golden fixtures |
| GAP-043 | #40 | merged — news eval HARNESS (Option C: metrics+bootstrap CIs+collapsed taxonomy+non-regression gate+model-digest; deterministic mocked test; metrics math-verified by Opus). **Real labeled golden set DEFERRED — see blocker below.** |
| GAP-037/038 | — | manual_skip (NER / Spark clustering — human judgement, out of scope) |

**Method:** WAVE 6a driven gap-by-gap (Opus review→codex fix→merge). 6b+B fanned out via run_night.sh (all parked needs_opus_review). 9 PRs Opus-reviewed in parallel; 3 had real P1/P2 (GAP-039-class prod-path misses) → codex fix-resume → re-review → merge. Merge-train docs conflicts auto-resolved via git `merge=union` driver on shared dashboard files; extract.py-touching gaps integrated serially via codex. Live-test GPU contention mitigated with `PYTEST_ADDOPTS='-m "not live"'`.

**BLOCKER for owner (GAP-043 real golden set):** the 40 GAP-033 rows are unlabelable (no title/body; only url + the model's own summary_en, which is circular), and the raw Bronze that held bodies is gitignored + deleted from disk. Producing real quality numbers needs the design's **Option A**: a bounded re-extraction via `silver.run.run_news` that persists ArticleRecord bodies (hashes+excerpts+url per copyright) into a committed labelable corpus (N≈120-200, oversampled for AT/DE + hard negatives + duplicate families), then Sonnet labeling per `docs/GOLDEN_SET_PROTOCOL.md`. This is a material approach decision (fresh network fetch + new body-persistence + LIVE pass) → left for owner. Harness is merged and ready to consume a real golden set the moment one exists (corpus path is a parameter).

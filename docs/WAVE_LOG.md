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

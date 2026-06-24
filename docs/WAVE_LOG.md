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

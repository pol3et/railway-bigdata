# GAP-011 Report And Presentation Implementation Plan

> Approved by this agent on 2026-06-24 after self-review. Scope is limited to GAP-011 report/presentation drafts, deterministic evidence-link tests, and required status/dashboard/progress documentation.

**Goal:** Create evidence-grounded report and presentation drafts under `output/` and guard them with a deterministic pytest checker.

**Architecture:** The report and slide outline will cite committed JSON evidence under `output/evidence/` only. The pytest checker will parse all cited evidence paths from both Markdown deliverables and load curated headline values from the backing JSON to catch missing paths and numeric drift.

**Tech Stack:** Markdown deliverables, Python standard library JSON/path/regex, pytest unit marker.

---

## File Responsibilities

- `tests/test_report_evidence_links.py`: unit test that asserts deliverables exist, all cited `output/evidence/...` paths resolve, and curated headline values loaded from JSON appear verbatim in `REPORT.md`.
- `output/report/REPORT.md`: course report draft with problem/dataset, architecture, proven World Bank Bronze->Silver->Gold result, MinIO storage result, Bronze source coverage, Spark evidence, known gaps, and evidence index.
- `output/presentation/PRESENTATION.md`: slide-deck outline using the same numeric claims and evidence citations as the report.
- `docs/GAP_REGISTER.md`: GAP-011 status/evidence row and Test Failure Mapping entry.
- `docs/TASKS.md`: `report/draft` status and Wave 3 contract state.
- `docs/STATE_AND_ROADMAP.md`: report/presentation status line and roadmap step.
- `docs/VERIFICATION.md`: dated GAP-011 verification subsection.
- `docs/index.html`: dashboard Report node/task chip reflecting that drafts exist and link-check tests guard evidence.
- `docs/PROGRESS_LOG.md` and `.planning/COURSEWORK_PROGRESS.md`: handoff/progress entries required by AGENTS.

## Tasks

### Task 1: Evidence-Link Test First

- [ ] Create `tests/test_report_evidence_links.py` before report/presentation files exist.
- [ ] Mark all tests `pytestmark = pytest.mark.unit`.
- [ ] Add a module docstring explaining that the test reads committed deliverables and committed `output/evidence/` JSON artifacts, not `coursework/` data or services.
- [ ] Implement helpers:
  - `_read_text(path: Path) -> str`
  - `_evidence_paths(*texts: str) -> set[str]`
  - `_load_json(path: str) -> dict`
- [ ] Test behavior:
  - Assert `output/report/REPORT.md` and `output/presentation/PRESENTATION.md` exist.
  - Extract every `output/evidence/...` path from both texts and assert each exists.
  - Load headline values from:
    - `output/evidence/inventory-live-2026-06-23/counts.json`
    - `output/evidence/inventory-live-2026-06-23/inventory_samples.json`
    - `output/evidence/minio-smoke/manifest.json`
    - `output/evidence/spark/manifest.json`
  - Assert each loaded value appears verbatim in report text, including formatted integer variants with comma grouping for large counts.
- [ ] Run `python -m pytest -q tests/test_report_evidence_links.py` and confirm RED because the deliverable files do not exist yet.

### Task 2: Report Draft

- [ ] Create `output/report/REPORT.md`.
- [ ] Include sections:
  - Problem & dataset.
  - Source table mirroring the Data Inventory scope.
  - Architecture with links to `docs/ARCHITECTURE.md` and `docs/DATA_CONTRACTS.md`.
  - Proven live World Bank Bronze->Silver->Gold result: 2,968 rows, 4 columns, 151 geos, 1995-2021, AT/HU 27 rows each, column names, and AT/HU 1995 samples, all cited to `counts.json` and `inventory_samples.json`.
  - Object storage with MinIO round-trip, buckets, and 32 B read/write cited to `minio-smoke/manifest.json`.
  - Bronze source coverage table citing committed manifest JSON files only, not raw Bronze paths.
  - Spark results from `output/evidence/spark/manifest.json`, because GAP-009 is closed in this checkout.
  - Known gaps linking GAP-013, GAP-006, GAP-023, GAP-019, and related open scope.
  - Evidence index table mapping headline claim to evidence path and JSON key/value.
- [ ] Keep claims honest: no live MinIO stats E2E, no live Ollama/news extraction, no Eurostat-to-Gold contribution.

### Task 3: Presentation Draft

- [ ] Create `output/presentation/PRESENTATION.md`.
- [ ] Use one `## Slide N` heading per slide.
- [ ] Include speaker notes as blockquotes.
- [ ] Reuse the same numbers and same evidence paths as `REPORT.md`; no rounded/new numeric claims.
- [ ] Cover title, problem, architecture, data sources, proven Gold result, MinIO storage, Spark result, known gaps, conclusion/next steps.

### Task 4: Status Docs And Dashboard

- [ ] Update GAP-011 row in `docs/GAP_REGISTER.md` to `closed` after verification passes, with evidence paths and verification command.
- [ ] Append Test Failure Mapping rows for `python -m pytest -q tests/test_report_evidence_links.py` and the full verify command.
- [ ] Update `docs/TASKS.md` to mark `report/draft` done and Wave 3 fast-track complete.
- [ ] Update `docs/STATE_AND_ROADMAP.md` report/presentation status and GAP-011 roadmap step.
- [ ] Add a dated GAP-011 verification subsection to `docs/VERIFICATION.md`.
- [ ] Update `docs/index.html` Report node/chip/metric for the dashboard sync rule.
- [ ] Append entries to `docs/PROGRESS_LOG.md` and `.planning/COURSEWORK_PROGRESS.md`.

### Task 5: Verification And PR

- [ ] Run `python -m pytest -q tests/test_report_evidence_links.py`.
- [ ] Run the user verify command exactly:

```powershell
python -m pytest -q tests/test_report_evidence_links.py && python -m pytest -q && python -c "import re,os,glob; missing=[p for f in ['output/report/REPORT.md','output/presentation/PRESENTATION.md'] for p in re.findall(r'output/evidence/[^\s\)\]\"`]+', open(f,encoding='utf-8').read()) if not os.path.exists(p)]; print('MISSING EVIDENCE PATHS:', missing); assert not missing"
```

- [ ] Run `python -m compileall -q src tests`.
- [ ] Run `git diff --check`.
- [ ] Commit, push `impl/gap-011`, open a PR against `main`, and verify mergeability/no conflicts.

## Self-Review

- Spec coverage: the plan covers both deliverables, the evidence-link checker, status docs, dashboard sync, progress logs, targeted/full verification, compileall, and PR creation.
- Scope control: no raw Bronze regeneration, no live collectors, no MinIO/Ollama/Spark execution, no source pipeline behavior changes.
- Current-repo adjustment: the older task text requested a Spark placeholder if GAP-009 was unbuilt, but local evidence shows GAP-009 is closed and committed; using `output/evidence/spark/manifest.json` is the evidence-grounded path and avoids a false pending claim.
- Placeholder scan: no implementation step depends on unspecified future work; open gaps are stated as gaps rather than filled.
- Test-first: the first implementation edit after this plan is the failing unit checker, followed by the report and presentation needed to make it pass.

# KSH STADAT Documentation Status Research - 2026-06-22

## Scope

Update documentation to make the `parser/ksh-stadat` task boundary explicit:
the Bronze KSH STADAT source work is complete, while scheduler wiring and
Silver XLSX parsing/tests remain open follow-ups.

## Local Files Read First

- `docs/PARSER_WORK_LOG.md`
- `docs/WORKSTREAMS.md`
- `docs/GAP_REGISTER.md`
- `docs/CODEMAP.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`
- `.planning/coursework/research/bigdata/ksh-stadat-seeds-2026-06-22.md`
- `.planning/coursework/research/bigdata/pr4-review-fixes-2026-06-22.md`
- `WIRING.md`

## Findings

- PR #4 addressed the `parser/ksh-stadat` Bronze source task.
- Current committed evidence for KSH live collection is
  `output/evidence/ksh-live-check-2026-06-22-current/manifest.json`.
- The active KSH seed set has six live-confirmed rail or rail-bearing XLSX
  tables.
- The stale or mislabelled seeds are documented as retired in the KSH source
  work: `sza0010`, `sza0006`, and the old `sza0009` passenger label.
- KSH scheduler wiring remains GAP-005.
- KSH XLSX -> `StatFact` parsing and Silver parser tests remain GAP-006.

## External Docs

No external documentation was needed. This was a repo-status documentation
change based on current local docs, code history, and committed evidence.

## Evidence

- Local search: `rg -n "KSH|ksh-stadat|STADAT|Silver|XLSX|StatFact|GAP-005|GAP-010|parser/ksh|KSH owner|KSH STADAT" README.md TASK.md docs .planning WIRING.md`
- Documentation-only verification: `git diff --check`

## Open Follow-Up

- Implement GAP-005 scheduler wiring for KSH.
- Implement GAP-006 KSH XLSX -> `StatFact` parser and Silver parser tests.

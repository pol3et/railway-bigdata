<!-- Keep PRs small and evidence-backed. See AGENTS.md. -->

## What changed

<!-- 1-3 lines. Which task slug(s) from docs/TASKS.md does this advance? -->

## Dashboard & status sync

Required if this PR changes pipeline state (advances/closes a gap, adds or wires a
parser, persists a layer, lands Spark/report evidence, or changes a source's
collection status). The dashboard is published from `docs/` via GitHub Pages, so
merging to `main` republishes it.

- [ ] `docs/TASKS.md` — task status / stage updated (or: no status change)
- [ ] `docs/index.html` — matching stage chip, source row, or metric signal updated (or: n/a)
- [ ] `docs/GAP_REGISTER.md` — gap advanced/closed with evidence (or: n/a)
- [ ] `docs/PROGRESS_LOG.md` — handoff entry appended

## Evidence

<!-- Real commands, outputs, row/col counts, generated file paths under output/evidence/.
     Do not claim a run/dataset/test/Spark result without a committed artifact (AGENTS.md). -->

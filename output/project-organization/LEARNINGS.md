# Learnings

## Lakehouse Separation

Bronze, Silver, and Gold should stay separate:

- Bronze lands raw bytes and provenance.
- Silver parses and validates structured records.
- Gold builds analysis-ready features.

This separation helps multiple people work in parallel and prevents accidental transformation of raw source data.

## Agentic Development

Future agents need durable routing docs because this project has stale historical references and two overlapping source layouts. A local `AGENTS.md` reduces repeated rediscovery and makes ownership boundaries explicit.

## Evidence Discipline

Course-project reports must be based on generated outputs. Documentation should say when code is implemented, when it is only designed, and when it is unverified.

## Big Data Requirement

The project currently has a lakehouse-shaped architecture but no verified Spark job in the current tree. A future phase should add Spark evidence with row counts, output paths, and generated analysis artifacts.

## Test-First Migration

The project now has characterization tests before deeper runtime wiring. This is important because moving files can otherwise hide whether failures were pre-existing or introduced by the migration.

The strict expected failure in `tests/test_pipeline_gaps.py` is useful: it proves the suite is tracking the known pipeline storage gap without pretending the end-to-end path works.

## Packaging

The package now uses a `src/railway_lakehouse` layout and editable installs. This prevents accidental imports from old working-directory paths and gives classmates one import root to use.

## Parser Evidence

A parser is not "working" just because its module imports or an HTTP request returns 200. The bounded live check showed several important cases:

- RSS and KSH produced usable raw artifacts with sidecar metadata.
- Eurostat produced a real catalogue, but dataset pulls failed because discovered codes need cleanup.
- World Bank produced a real catalogue, but one discovered indicator returned an API error payload.
- GDELT rate-limited the probe with HTTP 429.
- Statistics Austria returned an empty response for the configured seed.
- UIC returned 404 for the configured seed.

For collaboration, each parser owner should prove three things: a bounded live artifact exists, the raw artifact is stored unchanged with metadata, and a downstream Silver parser plan exists for turning that raw file into `StatFact` or `NewsFeature` rows.

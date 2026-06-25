# GAP-043 Synthetic News Golden Set Placeholder

`news_golden_set.json` is synthetic seed data for the deterministic evaluation
harness only. It is not the real Sonnet-labeled corpus and must not be cited as
model-quality evidence.

The real labeled corpus remains gated on the owner decision described in
`docs/GOLDEN_SET_PROTOCOL.md`: re-extract a bounded article sample that retains
labelable title/body evidence, then label it with the protocol. The harness
accepts a `--golden-set` path so that corpus can drop in later without code
changes.

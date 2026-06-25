# GAP-043 Golden Set Protocol

This protocol is for the future real labeled corpus. The current PR ships only
the deterministic harness plus a small synthetic seed fixture. The synthetic
fixture is not real model-quality evidence.

## Data-Availability Blocker

The current committed GAP-033 Silver sample cannot support real gold labeling:

- `NewsFeature` rows do not carry original article `title` or `body`; they keep
  only model outputs such as `summary_en`, which cannot be used as gold labels.
- The raw Bronze sample that contained title/body is ignored under
  `output/evidence/**/bronze/` and is absent from this checkout.
- URL slugs and model predictions are not enough to label reliable event type,
  sentiment, operators, monetary amounts, or duplicate groups.

Real labeling is therefore gated on an owner-approved bounded re-extraction
that retains labelable article evidence. Do not label from `summary_en`, and do
not fabricate article text.

The orchestrator directive referenced
`output/evidence/orch/gap-043/GOLDEN_SET_PROTOCOL.md`, but that file is not
present in this checkout. This committed protocol is reconstructed from the
GAP-043 directive plus the existing `docs/SPEC_NEWS_PREPROCESSING.md` and
`docs/GAP_TASKS.md` constraints.

## Corpus Shape

The real corpus should be supplied to the harness with `--golden-set <path>`.
Rows must include:

- `article_id`, `partition`, `source`, `url`, `published_date`.
- Evidence fields: `title` or a hash/excerpt/fetch-fixture reference; do not
  commit full third-party article bodies to the public repo.
- Gold labels: `language_gold`, `is_rail_related_gold`, `country_gold`,
  `event_type_gold`, `sentiment_gold`, `operators_gold`, `rail_lines_gold`,
  `monetary_amount_eur_gold`, `monetary_currency_gold`, `dup_group_id_gold`.

Partitions are mandatory:

- `TUNE`: threshold selection and prompt/dedup/FX/HU-offset iteration.
- `TEST`: frozen held-out gate and baseline reporting.

Never tune on `TEST`.

## Event Taxonomy

The harness stores the canonical 10-way event labels, then gates on the
collapsed 4-way taxonomy:

- `disruption`: `accident`, `strike`, `service_change`, `delay`,
  `line_closure`
- `development`: `investment`, `line_opening`, `financial`
- `policy`: `policy`
- `other`: `other`

The mapping is implemented as `railway_lakehouse.eval.news.EVENT_SUPERCLASS`.
Changing it invalidates baselines.

## Labeling Rules

- `is_rail_related_gold`: true only when the article is materially about rail
  transport, infrastructure, services, operators, policy, safety, or finance.
- `country_gold`: `HU`, `AT`, or `other`, based on the article's railway
  subject, not merely the publisher's location.
- `event_type_gold`: choose the most specific 10-way label supported by the
  article evidence; use `other` for non-rail or unsupported cases.
- `sentiment_gold`: document polarity about the rail subject: `negative`,
  `neutral`, or `positive`. If the target later changes to rail-system stance,
  document that baseline-invalidating decision.
- `operators_gold` and `rail_lines_gold`: list canonical names explicitly
  stated in the evidence. Empty list means no supported mention.
- `monetary_amount_eur_gold`: normalized EUR amount only when the evidence
  states an amount or explicit EUR equivalent; record original currency in
  `monetary_currency_gold`.
- `dup_group_id_gold`: same id for articles describing the same underlying
  event, including cross-border HU/AT duplicates and Dec-31/Jan-1 date-window
  cases.

## Agreement

Where feasible, run two independent stronger-than-pipeline labelers. Record
Cohen's kappa per categorical field. If agreement is weak for a field, mark
that field report-only until the rubric is clarified and labels are reviewed.

## Evidence And Copyright

Store enough evidence for audit without copying full third-party text:

- URL and fetch metadata.
- Content hash.
- Short excerpt within copyright limits.
- Optional private/local fetch fixture path if the owner approves it.

The public repo must not commit full article bodies or private/personal data.

## Harness Caveat

Every manifest carries this caveat:

`Agent-labeled silver-standard reference (Sonnet labelers, not human gold). Gates fire on NON-REGRESSION; absolute numbers are indicative only.`

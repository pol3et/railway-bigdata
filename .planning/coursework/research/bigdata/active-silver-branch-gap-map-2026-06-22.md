# Active Silver Branch Gap Map - 2026-06-22

## Question

Map the active teammate branches to existing gaps:

- `silver/news-rss-article-records`
- `silver/stats-worldbank-eurostat`

## Local Evidence

- `docs/GAP_REGISTER.md` says GAP-006 covers Silver reading Bronze
  fixtures/storage and writing auditable Silver outputs.
- `docs/WORKSTREAMS.md` splits GAP-006 between Silver Stats and Silver
  News/Feature Audit owners.
- `docs/WORK_SPLIT.md` defines Workstream D as Silver Stats and Workstream E
  as Silver News / Feature Audit.
- `docs/NEXT_SESSION_HANDOFF.md` says GAP-007 remains Gold loading from
  persisted Silver.

## Mapping

| Branch | Primary gap | Secondary contribution | Not owned by this branch unless added explicitly |
|---|---|---|---|
| `silver/news-rss-article-records` | GAP-006, Silver News half | GAP-010 only if it records bounded RSS/live evidence | GAP-007 Gold loading, GAP-009 Spark |
| `silver/stats-worldbank-eurostat` | GAP-006, Silver Stats half | GAP-010 only if it records bounded World Bank/Eurostat live evidence | GAP-007 Gold loading, GAP-009 Spark |

## Boundary

Both branches should produce persisted/auditable Silver outputs or fixtures that
Gold can consume later. They do not close GAP-007 by themselves unless they also
change `gold/run.py` or equivalent loading code and produce Gold row/column
evidence.

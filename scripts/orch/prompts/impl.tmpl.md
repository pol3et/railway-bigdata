You are implementing one task in the railway-lakehouse big-data course project.
The repo's `AGENTS.md` is authoritative and auto-loaded — follow its Hard Rules
(raw Bronze immutable; numeric stat merges deterministic, never LLM-rewritten;
outputs under `output/`; no fabricated data; tests must not depend on `coursework/`
data — use `tmp_path`/fixtures; keep the live dashboard in sync).

## Your task: {{GAP_ID}}

Implement it EXACTLY as written below. Do not widen scope.

{{GAP_SPEC}}

## How to work
- Drive this with your **`$ship-it`** workflow, with **NO Linear** — all context lives in
  this repo's code and docs (`AGENTS.md`, `docs/GAP_TASKS.md`, `docs/GAP_REGISTER.md`,
  `docs/DATA_CONTRACTS.md`, `docs/TASKS.md`, `docs/STATE_AND_ROADMAP.md`). Do not look for or
  expect a ticket.
- First write **one** implementation plan, **review and approve it yourself**, then implement
  strictly against that approved plan. Keep the plan scoped to this gap only.
- If you need ANY external research (library/framework APIs, exact config keys, a method or
  algorithm, version compatibility, course-domain background), use the **`/research-orchestrator`**
  skill and route through its MCP providers (Context7, Ref, Tavily, Exa, Firecrawl, LangChain
  Docs) — do not rely on memory or ad-hoc browsing. Cite source URLs for any external claim, and
  record the research in `.planning/coursework/research/bigdata/<gap-slug>.md`.
- Write **unit tests** and **integration tests**; MinIO is already running on
  localhost:9000 (compose `railway-minio`), so integration paths that need object
  storage can use it. Add a **short live test** only if the Definition-of-Done
  requires live evidence; keep it bounded.
- Run the task's **Verify** command and the full suite (`python -m pytest -q`) and
  make them green before you open the PR.
- If this changes pipeline state (advances/closes a gap, wires a parser, persists a
  layer, changes a source's status), update `docs/TASKS.md` + `docs/index.html` in
  the SAME change (AGENTS dashboard-sync Hard Rule) or CI will flag it.
- Branch `impl/{{GAP_ID_LC}}` is already checked out in this worktree. Commit, push
  to origin, and open a PR against `main` with `gh` (you have write access).

## Definition of done (do not stop until ALL are true)
- The task's Definition-of-Done checklist items are met.
- `python -m pytest -q` is green; `python -m compileall -q src tests` clean.
- A PR against `main` exists and is **mergeable** (no conflicts, CI reminder satisfied).

## Final output
When done, your final message MUST be a single JSON object matching the provided
output schema: the branch, PR url+number, which test tiers you ran and their result,
whether it is mergeable, which Definition-of-Done items are met, and (if you had to
stop early) blocked=true with the blocker. No prose outside the JSON.

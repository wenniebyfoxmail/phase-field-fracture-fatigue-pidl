# Research workflow adoption and Deep Research archive

Date: 2026-10-18. Scope: local research-agent workflow, not a scientific result.

## Adoption

| Surface | Observed / applied |
|---|---|
| Child-repository registered worktrees | 131 inspected |
| Non-historical workspaces | 103 receive the current bootstrap |
| Additional project roots | 5 receive the same bootstrap; 108 roots total |
| Recovery/historical/runtime snapshots | 28 preserved without a local overlay |
| Eligible workspaces with legacy-only AGENTS | 102; now routed through the installed core |
| Installed entrypoints | core, road adapter, PIDL adapter, figures, Deep Research |
| Existing research conversations/HQs | 28 notified; installed-skill read commands observed in all 28 |

The source inventory selects recent unarchived research conversations (seven
days) in the known research roots, with app inspection for HQ identities. It
does not label every branch an active experiment. Delivery and observed reads
are recorded separately in `installation.json` and `adoption.json`. Read receipts
do not prove every future response will comply.

The current bootstrap is maintained in
`docs/skills/research-decision-core/references/agent_bootstrap.md`. Each local
`AGENTS.override.md` reads the adjacent project rules and then this installed
bootstrap. [Official discovery rules](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
give the override precedence over `AGENTS.md` in the same directory; explicit
refresh messages address already-running conversations. The bootstrap preserves
machine, owner, frozen protocol, resource and run-authority conditions.

The overlay is excluded in local Git metadata so it does not dirty frozen run
snapshots. The tracked canonical AGENTS is updated for future checkouts. Local
installation is not a remote Windows/GPU deployment; those scientific code
snapshots were not changed. Historical copies were not deleted or rewritten.

## HQ and executors

Each HQ must pass the installed core, relevant adapter, active D step, scope,
budget and evidence/task pointers to live and future executors. Helpers return
to one owner record; completed helpers are not revived. The three Astra HQs and
the Portfolio HQ returned explicit adoption receipts. Their current task state
remains owned by their own records, not this rollout inventory.

Forty-five recent descendant records were checked individually: 22 not loaded,
22 idle and one initially marked active. App input to that multi-agent v2
helper was rejected, so its original parent was asked to forward via
collaboration. The helper subsequently became idle/completed before a refresh
receipt; it is not revived. No active helper remains among these records at
the recheck. Future delegation uses the refreshed HQ contract and local
bootstrap; we do not claim that completed helpers re-read the new workflow.

## Legacy entrypoints

- Old worktree `AGENTS.md` files still point to their own `docs/skills/` copies.
  Keep these for provenance; the dated overlay explicitly selects installed
  instructions for the current generic workflow.
- `0 idea test/AGENTS.md` previously excluded article material from Obsidian
  and coupled literature work to reproduction/review. The updated bootstrap
  replaces that generic policy: code/logs stay in the case, while reports,
  verified papers and reading notes enter the vault without waiting for a
  completed reproduction. Frozen scientific contracts are not loosened.
- Global installed pointers resolve to the maintained development worktree;
  do not retire it without repointing those five pointers.

## Deep Research workflow

`live question -> local reuse -> focused research -> report + sources -> smallest next test`

Invoke at topic intake, a useful brainstorming choice, or a measured bottleneck.
No compulsory research round or extra review per iteration. Use one living
report per question and reuse existing source records.

Reports go to `05 Knowledge/deep research report/`; verified papers and needed
analyses go to `01 Research Tracks/Paper Reading/`. Code and large data stay in
the project. The report begins with a short answer and preserves enough source-
located reasoning to choose an action. Task/Roadmap updates remain 2–4 lines.

If official retrieval fails, hand over title/DOI, exact official page and the
missing evidence. On “downloaded”, check identity, version, completeness and
readability, then archive and revise the synthesis. An inaccessible paper does
not prevent a useful provisional report. Preserve external research exports
and distinguish unverified citations from checked sources.

## Validation

| Test | Result |
|---|---|
| Independent forward test: non-road topic, existing review, three archived sources and two pending papers | Reuse first; provisional actionable synthesis; no road scientific assumptions or compulsory reproduction |
| Independent forward test: “downloaded”, vague filenames, different version, imported ChatGPT export | Match identity/version, preserve pending source, revise only after reading; imported citations remain unverified |
| Link helper: real local PDF copy plus valid note links | Exit 0 |
| Missing PDF link | Exit 1; missing reported |
| Duplicate note basename | Exit 1; ambiguity reported |
| Nested note basename containing a dot | Exit 0; extension appended without dropping version |
| Real vault: workflow note, existing task note and newly owner-archived research report | 8 wikilinks checked, no missing/ambiguous target |
| Skill metadata, Python compilation, diff whitespace | Passed |

Independent tester: `/root/deep_research_archive_forward_test`; read-only
scenarios, no retrieval or scientific run. The three earlier core/domain tests
remain in `../research_core_adapter_20261018/report.md`.

An actual owner also saved `Deep Research - 从可见裂缝几何到不确定性演化预测`
in the configured vault during this rollout. We checked archive links, not the
scientific correctness of that owner's synthesis. This demonstrates use beyond
the simulations without inventing a new research result here.

## Recheck

Run `python3 scripts/research_workflow_inventory.py` read-only for entrypoint
coverage; use compact app snapshots plus owner receipts for currently live
helpers. `deep-research-obsidian/scripts/check_archive_links.py` checks link
existence/uniqueness only, not paper identity or scientific verification.

# Current research workflow — local bootstrap

Read the adjacent `AGENTS.md` for project, machine, ownership and execution
rules. This bootstrap applies the user's 2026-10-18 research-workflow update
to this workspace, including its HQ and sub-agents.

## Minimal skill topology

`research-decision-core` is the sole default entrypoint. For one turn, load it
with at most one matching domain adapter and at most one task operator; do not
load the whole skill tree.

- For a road-fracture claim, the one domain adapter is
  `road-fracture-experiment-gate`. It loads `pidl-experiment-gate` only as an
  internal physics module when FEM/PIDL, Hard-5, or field semantics matter;
  PIDL/FEM is not an additional adapter.
- Use one operator only when needed: `deep-research-obsidian` for external
  knowledge, `research-figure-workflow` for a standalone result figure,
  `pidl-run-analysis-workflow` only for a frozen strict evidence package, or
  `research-review-channels` only when the user asks for a review.
- Writing, venue, Overleaf, and repository-asset skills are specialist tools,
  not alternative research entrypoints. `research-figure-color` is only for a
  mechanism schematic; `scipilot-figure-skill` is only for a clearly requested
  publication-grade complex data figure.

The core owns D1 reuse, the Decision Ladder, exploration/formal distinction,
fixed-benchmark policy, first-principles route changes, bounded authority,
visual explanation, and concise Obsidian updates. Do not restate those rules in
local cards. Follow the adjacent `AGENTS.md` for destinations and project,
machine, data, budget, and execution constraints.

The tracked canonical sources are `upload code/skills/<skill-name>/`; do not
route current work through retired `docs/skills/` copies. Archived worktree
copies are historical evidence, not current entrypoints.

# Legacy repository preservation register

## Purpose and boundary

This register records a recoverable Git snapshot of the legacy
`upload code` repository. It is a preservation record, not a code migration
plan, a research conclusion, or a worktree-retirement authorization.

The legacy repository, its remaining worktrees, and the top-level
`local_archive/` remain provenance and raw-evidence sources. New component
repositories may cite a specific upstream commit when they receive a bounded
component, but they do not inherit custody of the legacy repository history.

No branch, worktree, archive, raw output, or checkpoint is to be removed on
the basis of this register.

## Snapshot

| Field | Value |
|---|---|
| Snapshot date | 2026-10-26 |
| Legacy Git root | `/Users/wenxiaofang/0 Research/phase-field-fracture-with-pidl/upload code` |
| Register branch | `codex/infra-preservation-register-20261026` |
| Register base | `origin/main @ f32bd4301120d7f851b339d38881679e070c30b3` |
| Local branch heads preserved | 231 |
| Heads not contained by a locally cached `origin/*` ref | 79 |
| Remote state | Not refreshed or independently verified for this snapshot |

The two counts above are Git-object preservation facts. They do not classify
research activity, validity, or readiness.

## Recovery packages

| Package | Location | Integrity | Meaning |
|---|---|---|---|
| Local heads bundle | `/Users/wenxiaofang/0 Research/phase-field-fracture-with-pidl/local_archive/repository-preservation/git-bundles/2026-10-26/upload-code-local-heads-plus-detached-20261026.bundle` | SHA-256 `818363b8d49b1077af9462507d6086efbf9b550458b44313fee085a2faad528f`; `git bundle verify` passed | Every local `refs/heads/*` at snapshot, including the 79 tips not covered by locally cached `origin/*` refs. |
| Detached Stage-A bundle | `/Users/wenxiaofang/0 Research/phase-field-fracture-with-pidl/local_archive/repository-preservation/git-bundles/2026-10-26/upload-code-detached-s04-stage-a-launch-20261026.bundle` | SHA-256 `589203c1c0bec825e5cdbc881c29dc6af2d93783490a74cab012432b20393d7b`; `git bundle verify` passed | Preserves `03f9ae053f416684ea5cb3c3aa6b6d0175942437`, which had no local branch or locally cached `origin/*` ref. |

The Stage-A commit is also anchored locally as:

```
refs/preservation/20261026/detached-s04-stage-a-launch-20261022
```

The other detached worktree head,
`c883bfd8e4ecd37d2ae32dc3717a63db018f1ae2`, is reachable from named local
branches and locally cached `origin/*` refs; it is therefore already covered
by the local-heads bundle. It remains a separate checkout decision.

## What the bundles do not preserve

- uncommitted or untracked files in any worktree;
- ignored raw outputs, checkpoints, result folders, or local environments;
- the contents of `local_archive/` itself;
- a live remote hosting guarantee.

Those assets remain in their existing locations and require their own
path-level provenance and recovery checks.

## Recovery rule

Before recovering a ref, verify the bundle in an isolated recovery repository:

```bash
git -C <recovery-repository> bundle verify <bundle-path>
git -C <recovery-repository> bundle list-heads <bundle-path>
```

Restore only the named ref needed for a documented task. Do not overwrite an
active branch, treat a physical checkout retirement as migration, or infer
that Git recovery replaces raw-asset preservation.

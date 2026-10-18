# Request 28 Bundle-A Reconciliation

**Date**: 2026-08-18

**Scope**: commit/history review only

**Execution boundary**: no merge, cherry-pick, replay, experiment, commit or push
is authorized by this note.

## Decision

Do not merge `agent/fem-request-28` wholesale and do not cherry-pick its three
commits onto the dirty main checkout.

The twelve local LTPP commits `9fc0a44..4f9c8cf` remain intact. Request 28's
initial commit `e71ece3` is patch-equivalent to both `fc65daf` and `1176250`, so
neither duplicate should be applied. The later agent commits `e884524` and
`368a7e8` are useful intermediate semantic/audit records, but they are not the
terminal Request 28 decision.

The current terminal evidence is on the clean local worktree
`codex/kan-rbf-u012-micro@94d9c2b`:

- `f3bbc14` independently accepts the returned first-detect replay package;
- `94d9c2b` closes the frozen observability gate as
  `ENRICHED_RETROSPECTIVE_ENCODING_NEGATIVE`;
- the stop rule forbids a pairing/ROI/Williams/KAN rescue and forbids sparse
  earlier-origin requests under this gate.

The terminal branch has no configured upstream in the inspected branch list,
so it is a local preservation/integration risk. That observation does not
authorize publishing it.

## Commit-level findings

| Commit | Finding | Integration verdict |
|---|---|---|
| `e71ece3` | Initial Request 28 on top of the twelve LTPP commits. | Retain as historical request; do not present it as current terminal status. |
| `fc65daf` | Stable patch-id `37923738...`, identical to `e71ece3`. | Skip as duplicate. |
| `e884524` | Correctly distinguishes same-state cN/s4 packets from cross-cycle c(N-1)/s5 -> cN/s4 transition pairs and prohibits later-state substitution. | Preserve on its branch as semantic review evidence; do not cherry-pick as the current request because later execution followed the explicitly causal transition diagnostic. |
| `368a7e8` | Records archive audit, canonical-state0 replay need, and a pre-replay smoke gate. | Preserve as an intermediate gate; superseded by later replay acceptance and terminal analysis. |
| `1176250` | Stable patch-id `37923738...`, another duplicate of the initial request. | Skip as duplicate. |
| `8763516`, `fe61cc2` | Separate remote-preserved authorization/capture-amendment path. | Historical authorization evidence; not ancestors of the terminal analysis branch and not a merge target by themselves. |
| `f3bbc14` | Accepts the replay package after independent hash, flag, state-label and array checks. | Candidate terminal-evidence commit; review its dependencies before selective integration. |
| `94d9c2b` | Frozen three-case enriched-versus-plain gate returns a negative terminal verdict. | Current Request 28 research decision; candidate terminal-evidence commit after dependency review. |

## Why the agent branch is not the integration source

`agent/fem-request-28` branches from `699ae79`, before the twelve local LTPP
commits. A whole-branch tree comparison therefore appears to delete the LTPP
chain. This is ancestry divergence, not evidence that the LTPP files should be
removed.

The terminal worktree branches from the current `e71ece3` history, so it keeps
the twelve LTPP commits. However, it also contains a mixed fourteen-commit
KAN/RBF/diagnostic chain between `e71ece3` and `94d9c2b`. It must therefore be
reviewed by dependency and storyline; it must not be merged wholesale merely
to acquire the two Request 28 terminal commits.

## Scientific status after supersession

The accepted package contains the locked causal pairs:

| Umax | hidden source | event observation |
|---:|---|---|
| 0.11 | c121/s5 post-commit | c122/s4 first-detect peak |
| 0.12 | c82/s5 post-commit | c83/s4 first-detect peak |
| 0.13 | c58/s5 post-commit | c59/s4 first-detect peak |

The exact replay package passed the state/provenance gate, but the downstream
enriched retrospective representation failed: enriched beat plain on only
3/6 fold-target comparisons and Umax-only on only 3/6, with non-monotone
calibrations. This is retrospective event-aligned evidence, not early warning,
RUL, real-DIC inversion or real-road validation.

## Safe integration recipe

1. Keep `9fc0a44..4f9c8cf` unchanged.
2. Keep `e71ece3` once; skip its patch-equivalent duplicates.
3. Do not apply `e884524` or `368a7e8` as current status. Cite them only when
   the semantic/audit history is needed.
4. Review `f3bbc14` and `94d9c2b` together with their file-level dependencies,
   especially the audit/analyzer scripts and terminal experiment records.
5. Reconcile their terminal status into the shared frontier/inventory only
   after the dirty Bundle-X edits are isolated.
6. Preserve the current uncommitted Request 27 inbox addition; never resolve a
   Request 28 conflict by replacing the whole inbox file.
7. Run link, script and evidence-root checks in an isolated integration
   worktree before any commit or push decision.

## Dependency-audit update — 2026-08-18

The file-level audit is complete in
`docs/reviews/request28_terminal_dependency_audit_20260818.md`.

- `f3bbc14` passes a complete index-only patch check against `e71ece3`.
- The four core additions from `94d9c2b` pass individually.
- Its `docs/pidl_experiment_inventory.md` and `docs/research_frontier.md` hunks
  do not apply because they depend on other KAN-branch and stale index context.
- The terminal branch has no live remote ref and must be preserved deliberately
  only after a separate explicit integration/publish decision.

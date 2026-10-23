# D3 execution by case

`run_paired_windows.py --case c1` executes P1 and P2 for c1 only. The other
choices are `c83`, `c20s4`, and `c60s4`. Omitting `--case` selects all four.
This partitions execution, not the scientific case list: every manifest keeps
all four cases and binds a real initial network file for each one. Each arm
still has the identical 200 updates/block, 2000 updates/physical step and
10 outer-iteration limits; optimizer, starting weights, old-state semantics,
acceptance, persistence and stop rules are unchanged.

The authority must contain `requested_case` exactly equal to the selected case,
or explicit JSON `null` for all four. Its manifest SHA and implementation lock
must bind this version. An older envelope with that key absent is rejected.
Use one fresh output directory per disjoint case job; there is no automatic
retry or resume. A stopped arm does not become an accepted continuation.

## Input schema

`s04_e036_paired_windows_v2` remains the complete-input schema.
`s04_e036_paired_windows_v3` adds precisely one permission: an unselected case
may have both `predecessor` and `admission` set to JSON null while its real
network remains bound. All other keys and budgets remain identical. Available
references must point to actual files with matching SHA values, including
references belonging to unselected cases. No placeholder path/hash is valid.

Example case section in a v3 manifest for `--case c1` (angle-bracket values are
documentation placeholders, never runnable references):

```json
{
  "c1": {
    "predecessor": {"path": "<actual c1s0 NPZ>", "sha256": "<actual SHA>"},
    "admission": {"path": "<actual c1s0 admission>", "sha256": "<actual SHA>"},
    "network": {"path": "<fixed c1 initial network>", "sha256": "<actual SHA>"}
  },
  "c83": {"predecessor": null, "admission": null, "network": {"path": "<fixed c83 network>", "sha256": "<actual SHA>"}},
  "c20s4": {"predecessor": null, "admission": null, "network": {"path": "<fixed c20 network>", "sha256": "<actual SHA>"}},
  "c60s4": {"predecessor": null, "admission": null, "network": {"path": "<fixed c60 network>", "sha256": "<actual SHA>"}}
}
```

Selected null inputs, half-null pairs, null networks, omitted cases, unknown
case names, future targets and changed update caps are rejected. An all-case
invocation cannot use an incomplete v3 manifest. Selected predecessor content
and native admission undergo the existing checks before its optimization;
unselected cases create no output directories and perform no network forward.

`run_receipt.json` declares `requested_case`, `declared_cases`,
`execution_cases`, `deferred_cases`, `missing_unselected_predecessors`, and
`all_four_cases_selected`. `finished.json` records selected execution coverage
and outcomes; it is not a claim that all states passed physical acceptance.
Each bundle retains its actual case, manifest SHA, initial network and parent
lineage. Later manifests may fill deferred inputs, but must not replace or
reinterpret an earlier job's bound manifest.

## Per-case scorer collection

Implemented in `collect_paired_windows.py`; see `D3_COLLECTION.md` for the exact
current schema and CLI. Each case additionally binds `producer_scorer` so the
old/current protected replay and metric AST can be compared before scientific
scoring. The sketch below records the original proposal, not a runnable input.

The single-run scorer retains one actual receipt/manifest/root at a time.
Do not present four jobs as one fictional receipt or copy their output into a
fabricated common run. The collector retains the fixed target catalog and
the individual run bindings, extending the original sketch below:

```json
{
  "schema": "s04_e036_case_run_collection_v1",
  "case_runs": {
    "c1": {
      "training_manifest": {"path": "<real manifest>", "sha256": "<real SHA>"},
      "run_receipt": {"path": "<real run/run_receipt.json>", "sha256": "<real SHA>"},
      "callback_lock": {"path": "<producer implementation lock>", "sha256": "<real SHA>"}
    },
    "c83": null,
    "c20s4": null,
    "c60s4": null
  },
  "targets_catalog": {"path": "<same twelve-slot F1 target catalog>", "sha256": "<real SHA>"}
}
```

The actual run root is the bound receipt's parent directory. For each populated
record, require that receipt and authority select that same single case, bind
that exact manifest and callback lock, and retain all four declared cases.
Load that case's admitted predecessor and verify its own bundle chain with the
existing replay checks. Compare across shards the trajectory, mesh, effective
common physics, numerical budgets, all four fixed initial network identities,
and callback operator/controller identities. Different manifest SHA values
are expected when other inputs became available; compare the relevant actual
bindings, never rewrite the source manifest. Reject duplicate attempts for a
case rather than selecting the best result. A missing case remains missing;
failed endpoints remain diagnostic. No four-case overall aggregate until all
four genuine case records and required paired evidence are present.

The collector now reuses the scorer through an explicit single-case control
entry. Target arrays stay in scoring only.
The existing fixed benchmark result is reused. This control-only change uses
one direct metadata/source consistency check and no NN/FEM execution, additional
scientific test matrix, or review ladder.

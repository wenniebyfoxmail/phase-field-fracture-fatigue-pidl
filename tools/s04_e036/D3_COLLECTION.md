# Collecting genuine D3 case runs

`collect_paired_windows.py` consumes the actual per-case run receipts and their
own manifests/implementation locks. It calls the existing replay/metric body
once per available case. It does not synthesize a common run receipt, rewrite
the producing manifests, fill missing FEM states, optimize, or solve FEM.

The collection JSON has these exact keys:

| Key | Content |
|---|---|
| `schema` | `s04_e036_case_run_collection_v1` |
| `case_runs` | Exactly `c1`, `c83`, `c20s4`, `c60s4`; each is an actual record or JSON null |
| `targets_catalog` | Real `{path, sha256}` reference to one fixed 12-slot F1 catalog |
| `collector_sha256` | SHA of the current `collect_paired_windows.py` |
| `scorer_sha256` | SHA of the current `score_paired_windows.py` |
| `diagnostics_sha256` | SHA of `native_q4_diagnostics.py` |
| `q4_geometry_sha256` | SHA of `tools/s04_e011_analysis/run_multicycle_cross_replay.py` |

Each non-null case record contains exactly four `{path, sha256}` references:
`training_manifest`, `run_receipt`, `callback_lock`, `producer_scorer`. The last
is the **actual archived production version** of `score_paired_windows.py`,
whose SHA must equal that file's entry in the producing implementation lock.
For the first GPU snapshot this is the file frozen at commit `68291a0a`.
Use a genuine archived copy, not an invented hash or the new scoring file.
The run root is the actual `run_receipt.json` parent directory.

The receipt and its authority must explicitly select this one case, bind its
actual manifest and implementation lock, and declare all four scientific cases.
The selected predecessor remains fully admitted. The original four network
identities, trajectory, mesh, common problem, work/wall limits and production
implementation are checked across shards. Different per-case manifest SHA
values are retained; deferred FEM predecessors may have become available at
different times. Duplicate case keys or one receipt reused for multiple cases
are rejected. Select one actual authorized attempt per case; do not choose
between attempts based on the scores.

The target catalog remains `s04_e036_d3_targets_catalog_v1`, with exactly these
12 keys under `targets`:

```text
c1/s1 c1/s2 c1/s3 c1/s4 c1/s5
c83/s1 c83/s2 c83/s3 c83/s4 c83/s5
c20s4/s4 c60s4/s4
```

Each target is the real `{snapshot, admission}` pair or JSON null. In particular,
the failed c1/s4 state cannot become an F1 target, and c1/s5 cannot skip that
missing transition. `reference_tightening` keeps exactly c1/s2, c1/s4, c83/s2,
c83/s4, with real sensitivity records or null. A legacy catalog's optional
`training_manifest` is checked as provenance only; it is not falsely shared
across all case jobs. A new catalog may omit that single-manifest field.

## Source identity and numerical reuse

The new scorer separates only `score_paired_windows.py`'s postprocessing control
identity from its old producer lock. Before replay it compares the producer and
current AST of all twelve original metric/replay helpers, their constants and
imports, and the entire body of the per-case scoring loop. Any difference is
rejected. Every other production-lock file is still byte checked. The new
collector/scorer are separately SHA-bound by the collection. Training source,
controller, physics and run entry points are unchanged by this addition.

Missing targets preserve the existing behavior: PIDL persistence/own-history
chains can be verified independently and remain unscored. Failed endpoints
remain diagnostic; they are never accepted comparisons. The collector emits
all twelve declared slots, marking absent runs explicitly. It computes no
fixed-design aggregate unless all four case runs, all twelve targets and all
twelve verified P1/P2 endpoint pairs exist. This is an equal-state-weight
accepted-endpoint summary, not an equal-work estimate; the existing per-step
and cumulative-work diagnostics remain in each case result.

## Invocation

Pure I/O preparation check, without torch/project solver import:

```sh
python tools/s04_e036/collect_paired_windows.py \
  --collection actual_collection.json --output fresh_input_check.json \
  --check-inputs-only
```

Actual replay and native metric evaluation belong on the selected producer GPU.
Use a fresh output file and the execution owner's finite job timeout; this
example is an invocation shape, not an executed job or extra resource authority:

```sh
CUDA_VISIBLE_DEVICES="$SCORE_GPU" timeout --signal=TERM --kill-after=30s "$SCORE_SECONDS" \
  python tools/s04_e036/collect_paired_windows.py \
  --collection actual_collection.json --output fresh_score.json --device cuda:0
```

Source runs, targets and histories are read-only. The metadata-only check does
not certify numerical replay. Local preparation performs direct real-schema
and protected-source consistency checks only; the established fixed numerical
benchmark is reused, without an added scientific test or review ladder.

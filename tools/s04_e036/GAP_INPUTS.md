# Prepare matched comparison inputs

`prepare_gap_inputs.py` turns the four completed **main** FEM-B exports into D3
and D4 inputs. It does not run a model, load complete field arrays, assemble a
residual, qualify a new predecessor, or produce Stage A validation. Run it only
after all four real `targets.json` exports and their referenced files have been
retrieved. Missing files, missing hashes, wrong roles, broken predecessor chains
or incomplete windows stop preparation before any output is published.

The fixed task benchmark is:

```sh
python -m pytest -q tests/test_e036_prepare_gap_inputs.py
```

It uses one complete artificial four-window I/O fixture, validates D3/D4/fit
schema and target isolation, then removes a required input and checks that no
output is published. It is not numerical FEM/PIDL evidence.

## Command and request

```sh
python tools/s04_e036/prepare_gap_inputs.py \
  --request /absolute/path/gap_input_request.json \
  --request-sha256 ACTUAL_SHA256_OF_THAT_REQUEST \
  --out /absolute/path/FRESH_PREPARED_DIRECTORY
```

The request must contain exactly these keys:

```json
{
  "schema": "s04_e036_gap_input_request_v1",
  "input_inventory": {"path": "/actual/input_inventory.json", "sha256": "actual 64-character SHA256"},
  "network_inventory": {"path": "/actual/mechanism_network_inventory.json", "sha256": "actual 64-character SHA256"},
  "main_exports": {
    "c1": {"path": "/actual/c1/targets.json", "sha256": "actual SHA256"},
    "c83": {"path": "/actual/c83/targets.json", "sha256": "actual SHA256"},
    "c20s4": {"path": "/actual/c20s4/targets.json", "sha256": "actual SHA256"},
    "c60s4": {"path": "/actual/c60s4/targets.json", "sha256": "actual SHA256"}
  },
  "path_map": [
    {"source_root": "/original/archive", "local_root": "/retrieved/archive", "producer_root": "/mnt/data2/drtao/wennie/OWNED_JOB/data/archive"}
  ],
  "producer_output_root": "/mnt/data2/drtao/wennie/OWNED_JOB/data/prepared",
  "budget": {
    "updates_per_block": 200,
    "max_updates_per_step": 2000,
    "max_outer": 10,
    "step_wall_seconds": 3600,
    "job_wall_seconds": 86400,
    "cumulative_resource_limit": null
  },
  "mechanism_job_wall_seconds": 86400
}
```

Paths and hashes in this illustration are placeholders. The wall times are
examples, not fixed resource ceilings; each real job supplies its explicit
anti-hang settings. The D3 scientific comparison remains ten blocks of 200
updates. D4's solver settings and four canonical network hashes are read from
the runner's literal declarations through Python AST, without importing or
constructing a network. Both inventories are separately hash-bound.

The existing inventory locations relative to the project parent are:

- `local_archive/experiments/S04-E036/pidl_readiness_20261022/input_inventory.json`
- `local_archive/experiments/S04-E036/gap_attribution_20261022/logs/mechanism_network_inventory.json`

The eight canonical files have a local transfer receipt at
`gap_attribution_20261022/raw_archive/canonical_networks_20261022/transfer_receipt.json`.
Use its original remote `best_models` directory as one `source_root`, the local
`canonical_networks_20261022` directory as `local_root`, and either the same
existing remote directory or an owned copied directory as `producer_root`.
The generator independently hashes the local bytes; a transfer receipt alone
does not substitute for those files. It never opens a remote connection.

Every referenced artifact must match **exactly one** mapping. Mappings may use
absolute Windows source roots, but local and GPU destinations are absolute
POSIX paths. Do not overlap a broad project mapping with a narrower mapping
covering the same source. The same suffix is used under all three roots.
Add separate mappings for the inventories, original predecessor files,
converted NPZs, mesh/common files, completed FEM-B archives and canonical
network directory. Missing, ambiguous or colliding destinations are rejected.

## Outputs and transfer

- `d3_inputs.json`: four predetermined windows/endpoint inputs. Only each
  admitted old state and model0/model410/model98/model298 enter optimization.
- `d4_inputs.json`: four independent F1 s1/s3 old states and canonical
  model1/model3/model411/model413. No future target reference is present.
- `d4_targets.json`: separate target-fitting input, bound to the exact generated
  `d4_inputs.json` hash. Targets remain standard main F1.
- `d3_targets_catalog.json`: twelve main targets and four explicitly unavailable
  tightening slots. This is a catalog, **not** an executable scoring manifest:
  the final scoring manifest also needs the actual PIDL run receipt and producer
  implementation lock. Supply real tightening products separately when ready.
- `admissions/*.json`: path-only admission derivatives. Each preserves the
  original numerical metadata and points to the original JSON/hash in
  `path_relocation`. Original files and their hashes are unchanged.
- `prepared.json`: completion marker with every original source, verified local
  byte path, intended producer path, hash, derivative and generated file.

Copy generated files under the declared `producer_output_root` and source
artifacts to their recorded producer paths. Verify the recorded hashes after
transfer. The file only records intended destinations; it does not claim remote
deployment or permission to execute. An interrupted preparation without
`prepared.json` is incomplete. Stage A reuse and phase-specific execution
authority are handled separately by the existing tools.

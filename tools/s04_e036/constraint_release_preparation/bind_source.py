#!/usr/bin/env python3
"""Late-bind real terminal artifacts; pure I/O, never authorizes/launches a run.

Run only after the source job is complete. Paths and SHA values are discovered
from its actual supervisor argv and unique published terminal receipt.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from contract import CASE, SOURCE_JOB, argv_values, bound, read, ref, require, verify_source


def prepare(source_job, output):
    job = Path(source_job).resolve(strict=True)
    require(job.name == SOURCE_JOB, "bind only the prescribed C0 continuation")
    sa_path = job / "supervisor_authority.json"
    sa = read(sa_path)
    values = argv_values(sa["argv"])
    worker_output = Path(values["--out"]).resolve(strict=True)
    require(worker_output == job / "output", "source output is outside its job")
    wf_path = worker_output / "finished.json"
    wf = read(wf_path)
    require(wf.get("status") == "program_completed" and len(wf.get("outcomes", [])) == 1,
            "wait for the complete original program, never bind an interim checkpoint")
    outcomes = [p for p in worker_output.glob("outcome_*.json") if read(p) == wf["outcomes"][0]]
    require(len(outcomes) == 1, "source needs exactly one matching actual outcome receipt")
    candidates = []
    for path in (worker_output / CASE / "C0").rglob("completion.json"):
        receipt = read(path)
        meta = receipt.get("metadata", {})
        if (receipt.get("endpoint_complete") is True and meta.get("stage") == "lbfgs_final"
                and meta.get("arm") == "C0" and meta.get("dtype") == "float64"):
            candidates.append(path)
    require(len(candidates) == 1, "source must have exactly one real float64 terminal completion")
    terminal = candidates[0].parent
    ea_path = Path(values["--authority"]).resolve(strict=True)
    ea = read(ea_path)
    paths = dict(physics_manifest=Path(values["--manifest"]), worker_attempt=worker_output / "attempt.json",
        worker_finished=wf_path, worker_outcome=outcomes[0], execution_authority=ea_path,
        source_endpoints=Path(values["--source-endpoints"]),
        implementation_lock=bound(ea["implementation_lock"], ea_path.parent),
        source_snapshot=Path(sa["cwd"]) / "source_snapshot.json", supervisor_authority=sa_path,
        supervisor_attempt=job / "supervisor/optimization_probe_attempt.json",
        supervisor_started=job / "supervisor/optimization_probe_started.json",
        supervisor_finished=job / "supervisor/optimization_probe_finished.json")
    binding = dict(schema="s04_e036_constraint_release_source_v1", case=CASE, source_job_root=str(job),
        refs={k: ref(p) for k, p in paths.items()}, endpoint={k: ref(terminal / name) for k, name in
        (("completion", "completion.json"), ("bundle", "bundle.pt"), ("fields", "fields.npz"), ("network", "network.pt"))})
    verified = verify_source(binding, Path(output).resolve().parent)
    with Path(output).open("x") as stream:
        json.dump(binding, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return dict(source_binding=ref(output), source_clock=verified["source_clock"],
                approved=False, numerical_replay_performed=False, executed=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-job", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source_job, args.out), indent=2, allow_nan=False))

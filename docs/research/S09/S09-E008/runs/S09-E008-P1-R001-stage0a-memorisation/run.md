---
storyline_id: S09
experiment_id: S09-E008
run_id: S09-E008-P1-R001-stage0a-memorisation
execution_status: succeeded
retrieval_status: verified
scientific_verdict: negative
producer_alias: Taobo GPU
hostname: GPUServer8
gpu_visible_id: 0
gpu_uuid: GPU-980d2e42-c060-c272-b10b-8fbc204fef7f
started_utc: 2026-10-16T22:04:39Z
elapsed_seconds: 165.32039713859558
---

# S09-E008 P1 R001 run receipt

## Identity and launch

- reviewed commit: `f54327490ce8c02f6c042753d36ddcd32ecc5771`
- packet manifest: `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6`
- authorised config: `8aeec2b6f8c33b9d4efbeae57e4d20dd8f3e056ca9c0f9250e21c7c7466afe4f`
- PID: `4024406`
- runtime checkout: `/mnt/data2/drtao/wennie/S09-E008-P1-STAGING-20261016/runtime`
- output: `/mnt/data2/drtao/wennie/S09-E008-P1-R001-stage0a-memorisation`
- archive: `/mnt/data2/drtao/pidl_archives/S09-E008-P1-R001-stage0a-memorisation`
- stdout/stderr: staging `logs/run.stdout.log` and `logs/run.stderr.log`
- launch mode: detached; `CUDA_VISIBLE_DEVICES=0`; task-local tmp/cache
- dirty status: clean at launch
- retry status: no retry; this Run ID is consumed

## Completion

- exit code: 0
- optimiser steps completed: 1,000
- fully logged updates: 1,000
- last diagnostic update: 1,000
- stderr bytes: 0
- producer status: `SUCCEEDED`
- local retrieval: 13/13 output files matched the remote SHA256 inventory

## Frozen decision

- formal P1 pass: `false`
- capacity: false (`0.8541369 -> 0.7057137`, target `<=0.1708274`)
- growth: false (`0.000573133`, target `<0.000501735`)
- near-stagnant: false (`0.0000759554`, target `<=0.0000421613`)
- validity: true (finite; zero projected hard-constraint violations)

The execution succeeded while the scientific-performance gate failed. See
[`../../p1_run_analysis_20261016.md`](../../p1_run_analysis_20261016.md) for
the multi-objective and per-cycle mechanism analysis.

## Evidence pointers

- raw retrieved output: `local_archive/experiments/S09-E008/runs/S09-E008-P1-R001-stage0a-memorisation/producer_output/`
- post-gate launch evidence: `local_archive/experiments/S09-E008/runs/S09-E008-P1-R001-stage0a-memorisation/taobo_evidence/post_gate/`
- final execution review: [`../../p1_final_execution_gate_review_20261016.md`](../../p1_final_execution_gate_review_20261016.md)

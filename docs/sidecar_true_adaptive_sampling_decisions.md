# Sidecar Decision Memo: True Adaptive Sampling

**Status**: active memo  
**Branch**: true adaptive sampling / batch composition sidecar  
**Owner**: Mac-PIDL  
**Rule**: append-only

## Purpose

This file records branch-level decisions. Use it when we decide to promote, pause, retire, or redefine the sidecar.

Do not use this file as a run log. Per-run facts belong in:

- `docs/sidecar_true_adaptive_sampling_runs.md`

The canonical branch spec lives in:

- `docs/sidecar_true_adaptive_sampling.md`

## What belongs here

- opening the branch
- changing the hypothesis
- changing what counts as a valid implementation
- promoting one stage to the next
- pausing the branch
- retiring the branch

## Entry template

```md
## YYYY-MM-DD · <decision label>

- **Decision**: <promote / pause / retire / redefine / open>
- **Based on**: <run ids, files, or discussion anchors>
- **Reason**: <2-5 concise bullets or short paragraph>
- **Implication**: <what changes next>
```

## Entries

## 2026-05-12 · sidecar opened

- **Decision**: open
- **Based on**: `docs/sidecar_true_adaptive_sampling.md`
- **Reason**: this branch is the cleanest next test of the sampling-dilution hypothesis because it keeps the base Deep Ritz + Carrara objective fixed while changing collocation density or batch composition only.
- **Implication**: the first implementation target should be `S1-static-tip`; no weighted-energy variant should be treated as part of this sidecar unless the branch definition is explicitly revised.

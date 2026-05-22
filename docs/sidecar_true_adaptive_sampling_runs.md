# Sidecar Run Ledger: True Adaptive Sampling

**Status**: active ledger  
**Branch**: true adaptive sampling / batch composition sidecar  
**Owner**: Mac-PIDL  
**Rule**: append-only

## Purpose

This file is the run ledger for the true adaptive sampling sidecar. It records what was run, under which code/config state, and what the short verdict was.

This is not the place for long interpretation. Keep each entry compact. If a run changes the branch-level conclusion, record that in:

- `docs/sidecar_true_adaptive_sampling_decisions.md`

The canonical branch spec lives in:

- `docs/sidecar_true_adaptive_sampling.md`

## Required fields for each entry

- date
- run label
- code state or commit
- sampler type
- seed
- `Umax`
- horizon
- archive or output path
- key metrics
- short verdict

## Template

Copy this block for each completed run.

```md
## YYYY-MM-DD · <run label>

- **Code state**: <commit or local working state>
- **Sampler**: <S1-static-tip / S2-detached-score / S3-hybrid>
- **Seed**: <seed>
- **Umax**: <value>
- **Horizon**: <N=... or cycle range>
- **Config summary**: <only branch-defining knobs>
- **Output**: <archive path / log / figure path>
- **Key metrics**: <V4 / V7 / alpha_bar_max / process-zone metrics / N_f if available>
- **Verdict**: <one sentence>
```

## Entries

## 2026-05-12 · branch initialization

- **Code state**: documentation only; no implementation run yet
- **Sampler**: none
- **Seed**: none
- **Umax**: none
- **Horizon**: none
- **Config summary**: sidecar spec created; run ledger and decision memo initialized
- **Output**: `docs/sidecar_true_adaptive_sampling.md`
- **Key metrics**: none
- **Verdict**: branch opened as a documentation-first sidecar; first intended implementation target is `S1-static-tip`

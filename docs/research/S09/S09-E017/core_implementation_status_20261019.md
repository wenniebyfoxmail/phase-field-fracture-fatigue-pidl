# S09-E017 factorised core implementation status

Status: `CORE_IMPLEMENTATION_CANDIDATE__AWAITING_EXACT_COMMIT_REVIEW`
Date: 2026-10-19
Scope: local float64 numerical core and synthetic tests only

## Purpose

Implement the smallest reviewable part of the design-approved E017 pilot before
connecting it to a neural operator, FEM packet, optimiser or producer.  This
layer turns the amplitude-times-shape proposal into explicit arithmetic and
makes its multi-objective decision rules executable.

## Implemented contract

`source/s09_e017_factorised_pilot.py` provides:

- the capacity-supported `epsilon=1e-6` shape seed, stable exponential shape
  reallocation and weighted normalisation;
- a positive multiplicative amplitude residual with exact update-zero B25
  amplitude replay;
- the bounded irreversible decoder
  `Delta d = (1-d_pre) * (1-exp(-A*S))`;
- the common differentiable E016 effective amplitude/shape transform, including
  the legal zero-amplitude/undefined-shape branch;
- amplitude, shape and cycle-balanced field reconstruction objectives;
- update-zero gradient-scale freezing and the reviewed weighted PCGrad order:
  normalise, apply `(1,1,1,0.25)`, project against unmodified references,
  average active groups, then clip once;
- complete raw/scaled pairwise gradient geometry, projection, norm and merged
  direction diagnostics; and
- zero-compatible decision errors plus deterministic update-64 profile
  classification.

`tests/test_s09_e017_factorised_pilot.py` checks the seed TV bound, positive
mass-entry sensitivity, decoder bounds, amplitude replay, factorisation round
trip, zero-event semantics, signed reverse pairs, objective exact matches,
PCGrad beta ordering and conflict records, all-tie and mixed-profile boundaries,
and the amplitude-only active-group exclusion.

## Verification

The following local checks passed with the project Mac Python:

```text
/Users/wenxiaofang/miniconda3/bin/python3 -m py_compile ...
PYTHONPATH=source /Users/wenxiaofang/miniconda3/bin/python3 -m pytest -q \
  tests/test_s09_e017_factorised_pilot.py \
  tests/test_s09_e016_factorisation.py
/Users/wenxiaofang/miniconda3/bin/python3 -m ruff check ...
git diff --check
```

Result: `36 passed in 0.57s`; syntax, lint and whitespace checks passed.

The first attempted test command used the shell's active `agent-reach` Python,
which lacked pytest and stopped before collection.  The project-pinned Python
then ran the declared checks successfully.  No failed scientific execution or
retry occurred.

## Deliberate boundary and open review points

This candidate contains no neural-network head module, model forward, FEM or
packet reader, equilibrium residual implementation, autograd over a model,
AdamW object, optimiser step, training loop, SSH/GPU route, holdout or rollout.
It cannot yet establish runner readiness or any scientific result.

Three choices are explicit review targets rather than hidden assumptions:

1. the positive amplitude residual is `A_B25 * exp(r)`, which guarantees exact
   replay at `r=0` but was not written as a formula in the design card;
2. the shape objective uses equal internal weights on weighted half-L1 and
   one-minus-cosine, matching the design's equal-term intent but requiring an
   exact-code check; and
3. reconstruction consumes already-frozen positive per-cycle scales.  Their
   derivation, values and identities must be frozen in the later runner/config
   layer before the objective can be used; this core does not invent them.

## Allowed conclusion

The exact candidate can be submitted for core code review.  Even a PASS would
mean only that this isolated arithmetic is ready to serve as the base for a
separate no-training runner/config/evidence integration.


# Request 28 displacement observability track

## Mechanism question

Can peak displacement provide a compact observation bridge to the hidden
fatigue/process-zone state, and does explicit crack-oriented enrichment add
information beyond plain displacement gradients and load amplitude?

## Current status

**Closed negative for the frozen crack-enriched two-coordinate hypothesis.**

Request 28 supplied exact immediate pairs `c121/s5 -> c122/s4`,
`c82/s5 -> c83/s4`, and `c58/s5 -> c59/s4`; all state semantics and hashes
passed independent audit. The resulting independently reviewed offline gate
used only event displacement and geometry for PLAIN/ENRICHED representations,
with prior state used solely to score fixed `z_H,z_F` targets.

ENRICHED passed geometry coverage but was structurally nonmonotone and beat
PLAIN and Umax-only in only `3/6` comparisons each. No KAN, PIDL training, or
FEM replay was run.

## Claim boundary

This negative result rejects one fixed retrospective antisymmetric-opening
coordinate on three event-aligned Hard-5 trajectories. It does not prove that
all displacement measurements are uninformative, and it does not test early
warning. In particular, the plain strain-amplitude proxy tracked `z_H` with
small raw LOO error but a negative load-confounded slope.

## Evidence

- Lock and terminal result:
  `docs/experiments/request28_xdem_observability_gate_20260818.md`
- Independent review:
  `docs/experiments/request28_xdem_observability_gpt_pro_review_20260818.md`
- Script: `SENS_tensile/analyze_request28_xdem_observability.py`
- Local evidence root:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/request28_xdem_observability_gate_20260818/`

## Active next discriminator

Do not request event-relative earlier FEM states yet. If this line is reopened,
the next gate must be separately preregistered around a fatigue-exposure
coordinate that separates Umax from elapsed cycles, use fixed calendar-cycle
origins, and add independent trajectories. It may compare against the strong
plain-gradient observation; it may not retune the failed enriched operator on
these same three cases.

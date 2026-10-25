---
run_id: S09-E018-R002-amplitude-priority-ab
status: AUTHORISED_FOR_ONE_COMPLETE_RUN
authority: user instruction "请你推进后计算" on 2026-10-25
---

# E018 final run card (r2)

`R001` stopped before runtime construction, model creation, forward,
optimisation or an update because its new direct producer omitted the shared
resource-guard fields.  Its remote control root contains the one-shot failure
receipt and is not reused.  `R002` fixes only that control binding; data,
mapping, physics, two conditions and numerical budget below are unchanged.

Run one matched two-arm factorised damage-head comparison on Taobo GPU5.
Both arms consume the frozen E017 packet, B25 checkpoint, 16 exposed
independent transitions and beta=.25 native-Q4 AMOR equilibrium term.

| condition | trainable parameters | merge |
|---|---|---|
| `F_AMP_SHAPE_PCG` | amplitude residual and shape logits | symmetric weighted PCGrad |
| `F_AMP_SHAPE_A_PRIORITY` | amplitude residual and shape logits | amplitude-protected PCGrad |

The budget is 64 updates per condition, 128 total; no retry, resume, alternate
GPU, new FEM, holdout, rollout or checkpoint selection.  The producer checks
the exact packet/config/checkpoint SHA256 values, host and GPU identity, clean
tracked code, finite outputs, damage bounds, irreversibility, factorisation
roundtrip, 20 GiB reserved-memory cap and 1800-second wall cap.

At update 64 it saves all 16 transitions as `d_pre`, FEM/predicted `Delta d`,
and FEM/predicted `d_post`, and renders five-column field figures.  Completion
is only a verified execution state.  The scientific comparison is prospective:
the priority arm must improve high-event amplitude error without a diffuse
near-stagnant mass increase or a hard-constraint violation; otherwise merge
tuning stops and the next route is nonlinear readout/representation redesign.

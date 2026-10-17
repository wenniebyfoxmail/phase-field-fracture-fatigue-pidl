# Same-state representation and acquisition gap

Decision: G5 remains HOLD. This records the selected repair before any new
training or confirmation-field access. It does not change E013--E015 verdicts.

## Selected representation

Use s4 post-history-commit fields on both producers. The candidate manifest
`same_state_asset_manifest_20261012.json` records actual sources and unverified
fields; it is not an approved data lock.

| Target | Required source/reduction | Model treatment |
|---|---|---|
| d | FEM s4 nodal d reduced to declared cell support; PINN same-state current d with declared projection | direct Delta |
| alpha_bar | s4 committed history, GP-to-cell mean; matching PINN history timing/support | direct Delta |
| raw driver | s4 GP raw energy reduced on declared support; matching PINN evaluation | direct transformed Delta |
| mean f | mean of native degradation at same s4 state | optional direct auxiliary output, never f(mean alpha) |
| mean active driver | mean of native joint g(d_GP)*psi_GP with exact declared definition | exclude until qualified export; no product of mean parents |
| H | matched committed H support and timing | absent/masked until retained on both producers |

Direct cell heads learn declared output discrepancies. They are not exact
constitutive closures. The current PINN exports evaluate at FEM centroids;
this must be explicitly labelled and checked against the chosen target
projection, not called exact area integration. Physical inequalities and
irreversibility remain validation checks, not obtained by clipping data.

Retain C0 only if both genuine prehistory states exist. Fit features/scales on
inner/outer training trajectories only, use physical-cycle strata (C1--20,
C21--40, C41+), and keep event masks scoring-only. No confirmation-derived
normalization or FEM support enters deployable inputs.

## U0.115 verification

Independent method dialogue searched 477 model_settings files under bounded
Taobo roots and found zero exact-amplitude matches. This dialogue reused that
receipt and additionally queried `/mnt/data2/drtao/runs`,
`/mnt/data2/drtao/pidl-canonical`, `/mnt/data2/drtao/_pidl_handoff_v2` to depth9;
no model_settings candidates were returned. SSH `gpu-taobo` succeeded; alias
`taobo` is not configured and was corrected. No checkpoint tensors or training
were loaded. This proves no qualified match in the inspected inventory, not
global nonexistence across all unnamed storage.

FEM U0.115 has 103 cycles and is reuse-only. Without its PINN counterpart it
cannot be a fourth paired axis, and cannot be substituted with a checkpoint at
step115 or a monotonic load containing displacement0.115.

## Concrete next decision

Before any new PINN acquisition, prepare one fresh U0.115 acquisition run card
from the exact existing PINN family, with recovery, amplitude-derived cadence,
state/checkpoint retention, event scope, budget and stop rules frozen and
independently reviewed. It must provide actual trajectory states, not evaluate
a U0.12 checkpoint at U0.115 and label that a solved trajectory. The current
authorization advances D0 after G5; G5 does not pass with this missing axis.
No new training is launched from this note.

Once sources exist, export/match s4 from retained states, validate per-channel
support and projection, then review the completed data lock. The sole minimal
D0 is B0 zero-correction versus B1 closed-form direct-field ridge under
whole-Umax splits, <=5min/2GiB/100MiB. Its run card lives in the independent
method worktree `s04-direct-delta-audit-20261011/docs/research/S04/direct_delta_20261011/g5_method_review_and_d0_card_20261012.md`.
D003 is reused rather than rerun. A ridge miss is a diagnostic, not proof
that NN is impossible.

Execution owner: this dialogue for G5/data lock/D0. Method dialogue edits and
reviews method records only; no parallel export, D0 or training. Its independent
review agreed with HOLD and the spatial correction. Obsidian is updated here.

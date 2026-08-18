# Fixed-calendar fatigue-exposure track

## Question

Can observable peak deformation, after within-trajectory c1 normalization,
define a cumulative fatigue coordinate that transfers across Umax and beats a
simple load-times-cycle clock for hidden-state and remaining-life prediction?

## Current state

**Frozen and awaiting FEM Request 29.** The completed pre-gate confirms that
all retained c10/c20/c40 VTK displacement is s5 unload and unusable. In the
frozen ligament ROI, hidden mean history is strictly ordered by Umax at c10,
c20 and c40 (Spearman 1.0 at all three), so the missing displacement test is
informative rather than redundant. The archive still does not contain the nine
c10/c20/c40 s4 fields needed for the observability gate.

## Evidence and protocol

- Gate: `docs/experiments/fixed_calendar_fatigue_exposure_gate_20260818.md`
- Independent review:
  `docs/experiments/fixed_calendar_fatigue_exposure_gpt_pro_review_20260818.md`
- Producer note:
  `docs/handovers/windows_griphfith_request_29_fixed_calendar_exposure_export_20260818.md`
- Pre-gate evidence:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/fixed_calendar_fatigue_exposure_pregate_20260818/`

## Boundary

The current event-aligned PLAIN-to-history result remains retrospective. The
new gate uses fixed calendar cycles and forbids fitted powers, event-selected
origins, c50 rescue, and neural training. Until Request 29 is accepted and the
frozen gate passes, there is no exposure-based early-warning claim.

## Next action

Windows-FEM should reuse the Request 28 capture mechanism and replay each case
only from canonical c0/state0 through c40 if direct export is unavailable.
Mac then audits hashes/state timing before opening the nine displacement fields.

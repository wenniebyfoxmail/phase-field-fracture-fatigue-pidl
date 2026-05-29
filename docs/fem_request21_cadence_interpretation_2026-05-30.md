# FEM Request 21 Cadence Interpretation

Date: 2026-05-30

## Question

Does the remaining soft-hist0 FEM/PIDL gap mainly come from FEM using a
different within-cycle load/history-refresh cadence?

## Source

Windows-FEM completed Request 21 and pushed the summary in
`docs/handovers/windows_fem_outbox.md`.

Verified run-level results:

| FEM variant | Retained load factors | Penetration cycle |
|---|---|---:|
| Request 19 peak-only | `[1]` | no penetration by c120 |
| Request 21 n_step=2 | `[1, 0]` | 70 |
| Request 21 n_step=3 | `[0.5, 1, 0]` | 70 |
| Soft-hist0 standard | `[0.25, 0.5, 0.75, 1, 0]` | 69 |
| Request 21 n_step=10 | `[0.2, 0.4, 0.6, 0.8, 1, 0]` | 69 |

Generated figure:

```text
_analysis_fem_mechanism_20260528/figures/fem_request21_cadence_summary_20260530.png
```

## Reading

The large effect is not the number of positive substeps.  The large effect is
whether the cyclic solve retains the unload/end-of-cycle state.  Peak-only
does not penetrate by c120, but all variants with unload retained fracture at
c69-c70.

Therefore, after the Request 20 state-timing correction, the remaining
FEM/PIDL late-cycle field gap is unlikely to be explained mainly by FEM using
more positive substeps than PIDL.  A matched PIDL substep diagnostic may still
be useful, but it is no longer the highest-probability explanation for the
order-of-magnitude active-driver gap.

## Implication For PIDL

The current stronger hypothesis remains:

```text
PIDL alpha/damage evolves into a field that relaxes active psi_plus too much.
Then alpha_bar accumulation falls behind FEM, and the gap grows by feedback.
```

That is a representation/localization/optimization-path issue, not just a
cycle-indexing or substep-count issue.

## Caveat

The OneDrive field CSV/MAT payloads for Request 21 are present on Mac but were
still cloud placeholders during this pass; local reads/copies timed out and
produced zero-byte copies.  Field-level c20/c40/c69 probes should be run after
macOS hydrates:

```text
_pidl_handoff_reverseBC_u12_soft_hist0_nstep2_2026-05-29
_pidl_handoff_reverseBC_u12_soft_hist0_nstep3_2026-05-29
_pidl_handoff_reverseBC_u12_soft_hist0_nstep10_2026-05-29
```

The run-level conclusion above uses the pushed/verified outbox, not the
unhydrated local placeholder files.

## Next Step

1. Re-attempt local hydration and load the Request 21 CSV/MAT fields.
2. Compare c20/c40/c69 field probes across n_step=2/3/10/standard:
   `alpha_bar`, active `psi_plus`, `d`, near-tip integrals, and p99/p999.
3. If field probes also differ only weakly between n_step=2/3/10, deprioritize
   PIDL substep emulation and focus on branch-restart/staged-alpha/local-first
   representation diagnostics.

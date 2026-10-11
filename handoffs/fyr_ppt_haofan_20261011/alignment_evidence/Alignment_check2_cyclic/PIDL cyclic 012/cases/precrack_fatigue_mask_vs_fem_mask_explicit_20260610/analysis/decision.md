# Decision

Verdict: partial pass for the precrack fatigue-history mask; full field
residual comparison pending MAT hydration.

The Windows FEM Request 22/23 package passes the explicit-step export gate:
346 states are indexed, with `c1_peak -> step 3`, `c1_unloaded -> step 4`,
`c69_peak -> step 343`, and `c69_unloaded -> step 344`.

For the specific mask question, FEM+mask and PIDL+mask now agree on the retained
precrack fatigue-history state:

```text
left precrack audit band and mask support:
alpha_bar = 0
masked_Dalpha = 0
f_fatigue = 1
```

This is true at `c1_peak` and `c69_peak` in the focused region audit.

The analysis is not yet a full mechanism-alignment pass. The FEM export keeps
raw mechanics/raw `psi_plus` nonzero inside the masked precrack corridor, while
the PIDL diagnostic NPZ reports zero `psi_raw_elem` and zero `psi_active_elem`
inside the same region. This does not invalidate the fatigue-history mask
check, but it means raw-driver and residual-field conclusions inside the mask
need the full field-definition audit.

Blocked item:

```text
latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_state_fields.mat
```

is visible in OneDrive as 8.7 GB but currently occupies 0 bytes locally, so the
full residual-map script stalls on OneDrive hydration. Hydrate/download that MAT
before rerunning full FEM/PIDL residual figures.

# FEM psi mesh-scaling audit

| run | status | rows | last cycle | h_tip | psi_peak_max | psi_peak*h |
|---|---|---:|---:|---:|---:|---:|
|  | no FEM mesh-variant run directories found |  |  |  |  |  |

## Interpretation rule

If far-field/nominal psi remains stable while `psi_peak` increases as `h_tip` decreases, the large tip energy is likely a localization/mesh-resolution effect. If nominal psi drifts with h or peak values vary erratically, reopen the FEM unit/export definition audit.

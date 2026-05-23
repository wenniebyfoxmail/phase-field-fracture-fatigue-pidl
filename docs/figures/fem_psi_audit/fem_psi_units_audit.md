# FEM psi units audit

## Code-level semantics

- `solve_fatigue_fracture.m`: `psi_elem = mean(peak_psi_plus, 2)`.
- `AMOR.f90`: `strain_en_undgr = 0.5 * u^T B^T C_plus B u`.
- `at1_penalty_fatigue.f90`: Carrara accumulator uses `g(d) * strain_en_undgr`.
- Therefore exported `psi_elem` is raw cycle-peak tensile energy density.

## Nominal theory

For `E=1`, `nu=0.3`, `H=1`, `Umax=0.12`:

- `psi_sigma_xx_zero` = `0.0079120879`
- `psi_clamped_x` = `0.0096923077`
- `psi_1d` = `0.0072`

## Results

| case | Umax | theory sigma_xx=0 | theory clamped x | FEM far mean | far/theory free | alpha relerr far | scaling vs u12 | expected |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| u08 | 0.08 | 0.00351648 | 0.00430769 | 0.00283074 | 0.805 | 7.52e-06 | 0.444496 | 0.444444 |
| u10 | 0.10 | 0.00549451 | 0.00673077 | 0.00442302 | 0.805 | 7.49e-06 | 0.694522 | 0.694444 |
| u11 | 0.11 | 0.00664835 | 0.00814423 | 0.00535182 | 0.805 | 7.48e-06 | 0.840367 | 0.840278 |
| u12 | 0.12 | 0.00791209 | 0.00969231 | 0.00636843 | 0.805 | 7.46e-06 | 1.000000 | 1.000000 |

## Verdict

The far-field FEM `psi_elem` is O(1e-3 to 1e-2), follows Umax^2 almost exactly, and matches the cycle-1 accumulator to ~1e-5 relative error in the far field. This strongly argues against a global unit/export mismatch. The large crack-tip peaks should be audited separately as localization/mesh-resolution behavior.

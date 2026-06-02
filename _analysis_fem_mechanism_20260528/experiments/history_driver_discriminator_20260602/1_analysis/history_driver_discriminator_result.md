# History-Driver Discriminator Result

Reference: FEM Request21 `n_step=2 [1,0]`. PIDL saved index `j` maps to FEM cycle `c=j+1`.

## Event Timing

| mode | first boundary hit | confirmed stop | final alpha_bar max | final f_min |
|---|---:|---:|---:|---:|
| current active | 82 | 85 | 11.39 | 0.007069 |
| lagged g | 80 | 83 | 2383 | 1.76e-07 |
| raw driver | 81 | 84 | 2.323e+05 | 1.853e-11 |

## c69 Tip-Region Ratios

| mode | alpha_bar | Delta alpha_bar | psi_raw | g(alpha) | psi_active | history driver |
|---|---:|---:|---:|---:|---:|---:|
| current active | 0.4655 | 0.009087 | 1.52 | 0.9621 | 0.02039 | 0.009087 |
| lagged g | 0.6921 | 0.008207 | 1.545 | 0.9972 | 0.01838 | 0.008207 |
| raw driver | 5354 | 5017 | 1.55 | 1.066 | 0.02088 | 5017 |

## Reading

`lagged_g` and `raw` dramatically increase the accumulated history magnitude, but neither moves the event timing close to FEM `N_f=70`. The field gate is therefore more important than scalar `alpha_bar_max`: the driver can become huge while still not repairing the FEM-like process-zone evolution.

The cleanest signal is at c69.  PIDL has enough raw tensile energy density near the tip (`psi_raw` is about 1.5x FEM), but the active crack-driving energy (`g(alpha) * psi_raw`) remains only about 0.02x FEM for all three modes.  `raw` proves that making the history update large by itself is not sufficient: it explodes `alpha_bar`, but the active field and fracture timing still do not become FEM-like.

Decision: do not spend the next run only tuning the scalar fatigue-history driver.  The remaining gap is spatial/coupled: where the active process zone forms, how degradation suppresses it, and how the displacement/damage solve co-evolves.  The next useful branch should therefore be a process-zone/solver-path discriminator, for example strict FEM-mesh two-stage or local/domain-decomposed training with the gate fixed to `alpha_bar`, `Delta alpha_bar`, `psi_raw`, `g(alpha)`, `psi_active`, and boundary timing.

Generated files:

- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/history_driver_discriminator_20260602/2_figures/history_driver_discriminator_field_gate.csv`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/history_driver_discriminator_20260602/2_figures/history_driver_discriminator_scalar_summary.csv`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/history_driver_discriminator_20260602/2_figures/history_driver_discriminator_field_gate.png`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/history_driver_discriminator_20260602/2_figures/history_driver_discriminator_event_timing.png`

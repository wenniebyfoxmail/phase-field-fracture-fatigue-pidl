# S09-E003 physics probe evidence reading guide

Question: can a single-state displacement PINN reduce the native-Q4 AMOR assembled free-force residual while holding one accepted FEM damage field fixed?

Source: execution commit 2bfa5d3, protocol v1-equilibrium-pinn-c0, U012 c76 s4, effective U=.11999988. Raw source MAT and derived NPZ identity in input_manifest.json. Inputs live at local_archive/experiments/S09-E003/inputs; producer and retrieved output belong to R001.

Read native_audit.json first: derivative/export consistency, not teacher qualification. Then physics_decision.png/pdf from all scored history.csv evaluations: affine baseline1, frozen final-only threshold.8, physics residual history. Best-checkpoint values are diagnostics; final step500 alone decides the operational criterion. Native free-force RMS is reported separately and is not a new pass threshold.

physics_fields.png/pdf shows full-domain native versus FINAL PINN ux/uy and signed differences, with shared native/PINN color limits in each component. It is a one-state reference comparison, not supervised training or a physical-truth certificate. 450x450 nearest-native-node display is explicitly separate from the original native-node force metric. No crop, damage clipping or field smoothing. All nodes belong to one specimen-state; they are not independent trials.

physics_residual.png shows full-domain final free-node force magnitude, log10 display only; Dirichlet boundary reactions are excluded and masked. This is the spatial failure view for the one available evaluation unit, not uncertainty estimation.

Allowed conclusion: implementation agrees with declared FEM operators; if final ratio<=.8, this bounded optimizer reduces the selected assembled residual by at least20% from the affine initial condition. Forbidden: exact equilibrium, full teacher qualification, damage growth or fatigue rollout, PINO training, generalization, or physics outperforming data-only GNO. No graph-operator architecture was trained here.

Next interface: nodal u,d outputs and native GP state with honest substep timing; then matched data-only / equilibrium-only operator arms. Native AT1 penalty and fatigue kernel tests are ready, but those terms were not part of R001 loss.

Figures are produced by SENS_tensile/plot_s09_physics_probe.py from the scored final fields and history, without additional inference or training. Render inspection and independent evidence review are required before closure.

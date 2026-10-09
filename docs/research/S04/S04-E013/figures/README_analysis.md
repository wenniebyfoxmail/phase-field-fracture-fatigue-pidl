# S04-E013 Stage 1 decision figure

## Scientific question

Does the frozen 10,000-step supervised procedure pass every required field
gate at c20 early, c60 middle, c82 late and c83 transition, consistently over
seeds 1, 7 and 19?

## Evidence source

The figure is generated from the tracked compact copy
`../stage1_metrics.csv`. That file is an exact copy of the fail-closed
aggregate `metrics.csv` retrieved from Taobo matrix attempt B, runs R016--R027.
Its SHA-256 is
`4ee95024f1574c0e2a442c697d16f2904afd9ae08c64d81f9b54d7923ed4d85a`.
The rendering command is:

```bash
python ../plot_stage1_decision.py \
  --metrics ../stage1_metrics.csv \
  --output-dir .
```

## Reading order and metric definitions

Read left to right: displacement mass RMS divided by `|Us|`, native-Q4 strain
relative L2, and predicted weak-form `rho_u`. Each ordinate is the reported
error divided by its frozen gate, so the dashed line at 1 is the decision
boundary. Grey lines are individual seeds and the coloured line is their mean.
The exact essential-boundary error is zero in all twelve runs and is stated in
the title rather than placed on a logarithmic axis.

## Cross-panel interpretation

All points lie above their gate. Displacement remains around five times its
gate. Strain improves from c20 to c83 but remains roughly 17--24 times its
gate. `rho_u` is worst at c82 and declines at c83, while remaining about
71,000--113,000 times its gate. Thus the fixed procedure already fails at the
early state and does not show monotonic degradation into the transition state.

## Allowed and blocked conclusions

Allowed: the frozen supervised procedure has a reproducible 0/12 joint-pass
result, registered as `SUPERVISED_CAPACITY_FAIL_FIXED_PROCEDURE`.

Blocked: architecture incapacity, unsupervised physics failure, native FEM
trajectory reproduction, full FEM reproduction, or qualified FEM teacher.
The figure compares errors with frozen gates; it does not show field topology
or identify which change to the procedure would recover the fields.

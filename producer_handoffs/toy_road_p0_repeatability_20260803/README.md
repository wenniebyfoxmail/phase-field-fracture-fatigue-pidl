# Toy-Road P0 Repeatability Producer

This handoff implements the approved v2.1 producer contract. It is a synthetic
FEM transfer workflow, not real-road validation.

The production order is `P0 -> P0R -> T1 -> T2 -> T3`, with terminal validation
after every case. P0/P0R form one producer qualification pair and are not two
independent training or LOTO trajectories.

`finalize_toy_road_family_package.m` closes one completed case package using
its execution lock, c5 receipt, contract, and canonical attempt record. It
writes a no-clobber terminal manifest, sorted checksums, and validation summary.

Preflight receipts are explicitly non-authorizing. No production case may run
without a later, separate execution authorization.

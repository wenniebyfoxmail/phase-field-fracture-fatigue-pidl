# U0.12 KAN+RBF producer discriminator

Status: stopped at the frozen c1 same-state gate; quarantine.

## Frozen question

Does the exact compact KAN-displacement/RBF-phase representation from the c1
micro diagnostic become competitive when given the retained production
optimizer budget and full five-substep lifetime trajectory?

This run changes optimizer budget and trajectory/output retention only. It does
not widen the network or introduce a second architecture hypothesis.

## Launch record

- run id: `pf_kan_rbf_prod_d680ea3_20260818_004350`
- producer commit: `d680ea3`
- branch: `codex/kan-rbf-u012-micro`
- sync: Mac worktree rsync snapshot; not pushed
- Taobo code root: `/mnt/data2/drtao/wennie/pf_kan_rbf_prod_d680ea3_20260818_004350/code`
- Taobo archive root: `/mnt/data2/drtao/pidl_archives/pf_kan_rbf_prod_d680ea3_20260818_004350`
- GPU: physical GPU 0
- PID: `539448`
- launch time: 2026-08-18 00:43 Europe/London
- command: `/usr/bin/python3 -u run_kan_rbf_production_umax.py 0.12 --n-cycles 120 --seed 1 --epochs 10000`
- log: `/mnt/data2/drtao/wennie/pf_kan_rbf_prod_d680ea3_20260818_004350/logs/kan_rbf_u012_prod.log`
- initial health: CUDA available; 8 GPUs visible; GPU 0 initially empty; process
  cwd/cmdline and GPU occupancy verified after launch.

## Frozen semantics and gates

- `c0/state0` is initialization; the first physical cycle is `c1`.
- One physical cycle is `s1=0.25, s2=0.50, s3=0.75, s4=1.00, s5=0`.
- PIDL step `5*(c-1)+3` is the same-cycle s4 peak; `+4` is s5 unload.
- Primary event is `first_detect`; the later confirmation index is reported
  separately.
- Compare c1/s4 fields to the same FEM state and retained Formal MLP first.
- Then compare divergence trajectory and first-detect timing if the run reaches
  them.
- The run is not automatically promoted to paper evidence. External GPT Pro
  architecture review is unavailable, so the result remains quarantined.

## Result and stop decision

The production cap materially improved KAN displacement relative to the
300-epoch micro, but did not close the field gap:

- whole-domain displacement relative L2: KAN `0.070660`, Formal MLP `0.020951`
- process-zone displacement relative L2: KAN `0.047378`, Formal MLP `0.020677`
- whole-domain damage RMSE: KAN `0.041369`, Formal MLP `0.006744`
- damage >= 0.95 support ratio relative to FEM: KAN `2.318552`, Formal MLP
  `1.003144`

Visual QA retained the two representation failures seen in the micro: an overly
smooth crack-face displacement jump and parallel RBF ghost-damage bands. PID
`539448` was identity-checked and terminated after complete steps 0--6, while
optimizing c2/s3. No first-detect event occurred, and the partial trajectory is
not a censored lifetime datum. The exact compact 1,468-parameter formulation is
rejected; this is not a KAN-family rejection.

## Topology-coordinate / single-front follow-up

Commit `b5fb5a9` replaced the free 2D phase RBF grid with a monotone x-front
inside one even y-corridor and supplied five topology coordinates to a
5,459-parameter displacement KAN. The quarantined Taobo run
`pf_topologykan_c1_b5fb5a9_20260818_010801` completed U0.12 c1 only.

The intervention removed parallel ghost corridors, halved whole-domain
displacement relative L2 (`0.070660 -> 0.033636`), improved damage >= 0.95 IoU
(`0.431304 -> 0.506549`), and reduced support over-width (`2.318552 ->
1.974141`). It nevertheless worsened process-zone displacement relative L2
(`0.047378 -> 0.077971`) and process-zone damage RMSE (`0.067406 -> 0.088816`).
The single corridor is too thick and extends too far ahead of the FEM c1 tip.

Verdict: mixed morphology improvement but failed frozen joint gate. No lifetime
continuation. Post-run GPT Pro review accepts no-lifetime and closure of broad
coupled sweeps, but permits exactly one identical pretraining-off c1 diagnostic
to resolve the initialization/pretraining confounder. No tuning, alternate
seed, width change, second rescue or automatic lifetime launch is allowed.
Ghost-band removal must be described as constraint-enforced topology behavior,
not learned fracture-mechanism recovery. The result remains quarantine because
the field gate failed; the external-review gap is now closed.

# U0.115 PINN terminal audit and G5 update

Execution succeeded: exit0, child stopped, no cleanup errors. London finish
2026-10-12 22:51:53; elapsed15,364.45s (~4h16min), well inside48h/50GiB.
No retry, resume or second solve was executed.

Run `pf_u0115_acquire_39f8108fe96d406385e4011700cb47f9`.
Source b6d5610, source manifest2ad7b6a3...301f6c; supervisorfccba7a4...682e7b.
Raw output stays on Taobo. Control evidence and archive identity manifest are
retrieved into `local_archive/experiments/S04-E016/u0115_pinn_acquisition_20261012/terminal_audit/`.

| Audit | Result | Scope |
|---|---|---|
| Checkpoint coverage | 503 consecutive files, raw steps0..502 | actual saved states |
| Model/history load | model for each saved step and required finite tensors, no failures | serialization/finite validity, no forward-field/PDE validation |
| Physical state coverage | c1..c100 s4/s5 complete; c101 s1/s2 terminal tail | same-state export candidates |
| Native event | first step499=c100/s4; stop step502=c101/s2 | native PINN confirmation counts3 raw training steps |
| Archive freeze | 1,894 files; 4,849,185,351 bytes | raw-byte identity |
| Archive manifest SHA | ddd2e4f4c247e3b5aeb7bcae409b6a579c6f9a02c1337d0770da94fda48d4326 | sealed external inventory |
| G5 | HOLD_MATCHED_PROJECTION_AND_FIELD_EXPORT | no D0/NN release |

The log says “cycle502”, but its counter is the raw training step. The native
counter decrements each loop iteration, not each physical five-substep cycle.
The frozen acquisition preserved this historical PINN behavior. Do not equate
its three-step confirmation with FEM's three-physical-cycle tail, call502
physical cycles, or relabel the terminal as an s4/s5 state. The own-pre-event
s4 candidate window is c1..c99; common-pre-event still requires the declared
FEM event/state mask. Event values are scoring/qualification information, not
features or stopping information for a future deployed corrector.

The 120-cycle schedule was a ceiling under native termination, not achieved
120-cycle coverage. Successful native termination supplies complete own-run
lineage, not a full103-cycle pairing with FEM or a finished G5 data lock.

Support is now explicit: PINN hist_alpha is45591 nodes; hist_fat,
psi_history_elem and psi_plus_prev are90000 triangle-element values. FEM
has86756 nodes and86408 Q4 cells/4GP. Therefore no raw indexwise Delta or
exact GP-derived f/active claim is admissible. Use the reviewed reduced-field
route only after explicit projection/reduction and same-state mapping review.
Current checkpoint history is post-commit, whereas retained gradient
diagnostics are explicitly pre-history-refresh and cannot be substituted.

Unique next action: reuse existing export/mapping tools to assemble s4 field
and causal-history exports from the qualified saved-state candidates; verify
mapping containment, fields, precision, timing, loads and deployable-input
pipeline. Then independently review G5's completed data lock. U0.1175 remains
sealed confirmation, U0.125 closed. D003 is not repeated. This dialogue owns
G5/export/D0; method dialogue remains read-only reviewer.

Audit resource note: first read-only audit was stopped by exact own PID after
it used127 CPU threads; no raw asset was changed. The completed audit capped
Torch/BLAS at4 threads in a fresh audit directory, used CPU only, and loaded
weights_only checkpoints without model evaluation or training.

# Proposed first-state diagnostic — not launched

Purpose: identify whether R001 failed alpha minimum, alpha maximum or local
healing. Native first-state convergence alone did not distinguish them, and
the rejected vector was not retained. This missing observable prevents a
justified initialization/constraint repair; it is the only reason for repeating
this known first-state calculation.

Candidate code: `a5d65d21ff185194f6d54fbc5feaa918becc2732`, independently
read-only reviewed. Same E/nu/Gc/ell, AT1/AMOR, Q4 mesh, soft initial profile,
boundary conditions, U=.03 and unchanged residual/damage thresholds. Only
changes: emit each invariant, save rejected field before asserting, allow
explicit one-state prefix, preserve distinct full/prefix completion, and
capture actual child exit correctly. No relaxed tolerance or physics change.

Proposed Run ID: S04-E035-R003. Authorised producer if approved: CITPC12 via
`citpc12-ssh`; fresh root `C:/q4runs/S04-E035-R003-20261020`.
Entry: `run_shear_fem('C:/Users/xw436/GRIPHFiTH',
'C:/q4runs/S04-E035-R003-20261020/fem',1)`.
Child timeout: 90 seconds, enforced by the supervisor's remaining-time wait;
new total producer envelope 180 wall seconds including staging/admission,
one no-solve syntax check and retrieval. One diagnostic attempt; no automatic
restart. No GPU, no PIDL training, no full trajectory. Output ceiling 10GiB;
expected <15MiB from observed R001. No shared environment/source modification.

Admission: no competing MATLAB process; source/runtime paths and task snapshot
match; no existing output/launch receipt; storage headroom. A failed/unknown
launch is inspected, never repeated blindly. On timeout or native failure,
retrieve the existing files and stop.

Result: exact rejected p_field/p_field_old/displ, U/state/support metadata,
final residuals, alpha_min/alpha_max/max_healing, logs and native exit status.
Interpretation: diagnostic only, regardless of success. If the invariant
failure repeats, retain that failure and use its spatial pattern to design a
reviewable repair; do not loosen thresholds, switch models or launch a full
rerun under this diagnostic permission.

Authority: **pending a fresh decision after R001's scientific stop**. This
document and code readiness do not authorize another calculation. The original
request remains the eventual full shear FEM/PIDL comparison; this small
diagnostic resolves a specific unobserved blocker on that route.

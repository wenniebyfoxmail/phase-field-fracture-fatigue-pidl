# Windows-FEM Request 31 v2 amendment — read-only repair and exact launch scope

Date: 2026-10-08

Status: `READY_FOR_CHATGPT_REREVIEW`

Authority: this amendment does **not** issue `LOCK_ACCEPTED_PROCEED` and does
not authorise a long FEM run. The v1 `FAIL_HOLD` receipt remains immutable.
The numerical tolerance remains `1e-12`.

## Canonical identity lock

The v2 read-only audit is bound to:

- source commit `862992a60edc7f59335365beacb5c71fc8592a7a`, clean;
- snapshot `hard5_stage0b_862992a60edc7f59_b5c39464cd4091f6`;
- snapshot manifest SHA256
  `33443ef261ae529c6f57814d518fc4a5c905d94286bf835a83a06cd9733d522c`;
- `solve_fatigue_fracture.m` SHA256
  `82cf9d7f1d566c92cbb659c62d1a4ad6c41f827c1470d6f23bde6dd34ea2aad4`;
- canonical `state0_analysis.mat` SHA256
  `91b8f89ba3a211f08f1b79def5d2d50a973798e988deedc5c5c7e3b64a98ef11`;
- native AMOR MEX SHA256
  `ac9f5d5eacafa94434d5aab5bac3f3b2d003b9a540969122589d44ce9d095c63`;
- native fatigue/history MEX SHA256
  `cc9d673b44bfa6188aa269dbfd2c12829cbacd4d00de12103195731d13228494`;
- 86,756 nodes and 86,408 native-order Q4 elements;
- nominal load factors `[0.25, 0.50, 0.75, 1.00, 0.00]`;
- effective load factors `[0.249999, 0.499999, 0.749999, 0.999999, 0]`;
- for U0.115, actual imposed displacements
  `[0.028749885, 0.057499885, 0.086249885, 0.114999885, 0]`;
- unchanged detector: right-side `x>=0.48`, `d>=0.95`, at least three nodes,
  first hit plus three confirmation cycles.

The allowed run-to-run differences are only amplitude-derived load values,
cycle/stop scope, output identity, run ID/path/receipt metadata, and execution
mode. Physics, mesh/order, state0, kernels, cadence, tolerances, update order,
reduction definitions, and detector are invariant.

The old U0.115 mesh arrays match the v2 identity exactly. Its base-config hash,
qualified source commit and declared changed-field set also match; the different
post-change config hash is explained by run identity/receipt metadata.

## Two separate field contracts

### Contract A — cycle summary

This is not a simultaneous peak state:

```text
psi_cyclemax_elem = mean_GP(max_s1..s5(raw psi_plus_undamaged_GP))
d_s5_elem         = mean_Q4_nodes(d_node after s5 history commit)
alpha_bar_s5_elem = mean_GP(alpha_bar after s5 history commit)
f_alpha_s5_elem   = mean_GP(f(alpha_bar) after s5 history commit)
```

The serialized field is named `alpha_bar_elem`; `alpha_elem` is retired from
the v2 contract.

### Contract B — same-state s4 nodal fields

```text
u_node = cN/s4 post_history_commit
d_node = the same cN/s4 post_history_commit
```

The s4 `history_gp` is the history already committed after the s4 refresh. It
is not a prior-state input. The causal prior is `cN/s00 pre_cycle_committed`:
c1/s00 is state0; later s00 rows alias c(N-1)/s5.

## Correct cyclemax gate

Independent c1 recomputation proves
`mean_GP(max_substep(raw psi_GP))` equals the exporter with max-abs error zero
under the unchanged `1e-12` tolerance.

The audit explicitly distinguishes the incorrect order
`max_substep(mean_GP(raw psi_GP))`:

- actual max-abs difference: `0.343442979681015`;
- 297 elements differ above `1e-12`;
- synthetic sentinel: correct order `10`, wrong order `5`.

`cyclemax-s4` is diagnostic only. There are 46,329 strict GP differences out
of 345,632 (`cyclemax-s4 > 1e-12`), with maximum `28.903499728380883`.
MATLAB's first-occurrence argmax is used for descriptive substep counts;
`N_strict` is tie-independent. No ties occurred within `1e-12` in this smoke.

## c1 smoke disposition

All five physical rows are unique s1..s5 `post_history_commit` states. All
required dynamic arrays are finite; every substep reports converged; top and
bottom displacement BC errors are at most `3.47e-18`; and independent s5
reductions for `alpha_bar_elem`, `f_alpha_elem`, and `d_elem` match the exporter
with max-abs error zero. The smoke stopped after c1. No Phase B run followed.

## Existing U0.115 reuse decision

The August archive contains 103 cycles and 618 logical rows:

```text
103 * (one logical s00 prior row + five physical s01..s05 rows) = 618
```

The 516 unique payloads are state0 plus 103*5 physical substeps; later s00 rows
alias the preceding cycle's s5. It contains one Contract-A file per cycle and
one native Contract-B s4 `u_node+d_node` state per cycle. Sampled beginning,
middle and terminal s4 states pass shape and finite checks. The unchanged
detector produced a first-hit stop followed by the required three-cycle tail.

Decision: `readonly_reuse_and_reseal_no_new_fem_solve`. The old per-run receipt
did not independently establish capture neutrality against an uninstrumented
reference, so reuse is limited to the qualified captured-source family and the
v2 identity/semantics contract; it is not a new neutrality claim.

## Existing U0.125 contamination verdict

The audit did not open any U0.125 scientific payload. Metadata show that the
case is amplitude-named, co-located with U0.115, and accompanied by a visible
top-level event-evidence file rather than a dedicated opaque access-controlled
holdout archive. No reliable access log exists. Absence of a tracked
propagation record, hashes, and timestamps cannot prove non-exposure.

Verdict: `exposure_unknown_not_cleared`. U0.125 is not eligible as the sealed
confirmation trajectory and must remain closed unless a later protocol
explicitly reclassifies it.

## Metadata-only Umax inventory and exact scope

Known generated Hard5 amplitudes under the audited Windows producer root are
`0.11, 0.115, 0.12, 0.125, 0.13`. No directory-generation metadata match was
found for the frozen candidate order `[0.1175, 0.1225, 0.1275]`.

The preregistered selection rule chooses the first metadata-clear candidate;
therefore the conditional fresh confirmation amplitude is `Umax=0.1175`.
This is an interpolation confirmation only.

Exact scope now:

- authorised long runs: **zero**;
- U0.115: read-only reuse/reseal, no solve;
- U0.125: remain closed, not a confirmation run;
- only after ChatGPT re-review and explicit authorisation: one fresh U0.1175
  long run exporting both Contract A and Contract B.

## Windows evidence root

```text
C:\q4runs\request31_v2_readonly_audit_20261008
```

Fresh report hashes are recorded in that root's `SHA256SUMS.txt`. Final state:
`READY_FOR_CHATGPT_REREVIEW`; execution state remains
`AWAITING_CHATGPT_REREVIEW`.

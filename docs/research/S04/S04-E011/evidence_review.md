---
review_type: independent-evidence-review
reviewer: ChatGPT Pro
reviewed_at_local: 2026-10-06
source_chat: https://chatgpt.com/c/6ac3d374-50b4-83ed-893c-02fa7d0a71f4
verdict: PASS
---
# S04-E011 independent evidence review

This is a faithful normalized record of the external review. The reviewer assessed the supplied source excerpts, definitions, tables, and decision package. It did not independently open the repository, inspect the original archive, or recompute the vectors.

## Verdict and claim boundary

**Evidence PASS**, bound to the original Stage0b producer commit `53ce560b6d20b336d6ec92ccf56ed2b230e804ce` and to the 18 audited states.

The source path supports the sequence UV solve → damage solve and bounds → accepted-pair UV reassembly using updated damage and current UV → native stopping check → export/history commit. The claim that Stage0b skipped the post-damage UV check must therefore be withdrawn.

The review does not withdraw the teacher-screen failures. All 12 nonzero loading/peak states fail the frozen `rho_u <= 1e-3` gate, so every `full_teacher` result remains `NOT_QUALIFIED`. The result is not evidence of true-solution error, mesh convergence, complete teacher qualification, or any unsampled state.

## Required semantic corrections

- `producer_metadata.equilibrium_residual` is the scalar returned by the preceding UV Newton solve. It is not the accepted-pair residual reassembled in `post_iter_update`.
- `accepted_pair_raw_uv_l2` is the Euclidean L2 norm of the reassembled accepted-pair UV residual on the free/active UV DOFs.
- `native_phase_residual` is the archived scalar returned by the phase-field Newton solve and then passed into `post_iter_update`. The producer applies the damage bounds after that Newton return and does not reassemble a projected hard-KKT residual for the native staggered check. It must not be conflated with the E010 projected hard-KKT L2.
- `native_stagger_sum = accepted_pair_raw_uv_l2 + native_phase_residual` is reconstructed after the fact from those two recorded components. It was the source-level stopping expression, but a final accepted `res_sum` scalar was not separately archived.
- `rho_u / accepted_pair_raw_uv_l2` is about `4.17e3–4.44e3` for these sampled residual directions. It is not `rho_u / native_stagger_sum`, and it is not a universal unit conversion because it depends on the residual's spatial distribution over nodal masses.

For the sampled directions, the teacher threshold corresponds to a raw UV L2 of roughly `2.25e-7–2.40e-7`. By contrast, the native UV allowance is state dependent: `accepted_pair_raw_uv_l2 <= 4e-4 - native_phase_residual`.

## Accepted conclusion

The reviewed Stage0b producer reassembled and checked the free UV residual after the damage update. All 18 selected states pass the reconstructed original native acceptance expression, while all 12 nonzero loading/peak states fail the later mass-dual teacher UV gate. The different acceptance criteria explain the differing pass/fail labels; the evidence does not support attributing them to an omitted final UV check. Residual remains, but its contribution from the final damage update has not been quantitatively identified.

## Route decision

The review recommends freezing two distinct estimands before seeing PIDL results:

1. **Primary strict-physics route:** create a “fixed accepted damage / frozen fatigue UV-rebalanced derived reference field.” Do not call that derived field a qualified FEM teacher unless all other teacher gates also pass.
2. **Secondary native-fidelity baseline:** ask whether PIDL reaches the original FEM output accuracy under the native acceptance contract. Native residual pass alone does not prove the same field, so displacement and damage field metrics must also be preregistered.

The decision rule may not be “either route passes = success.” Each route retains its own claim and threshold.

## Minimum next experiment

First close the read-only definitions of raw UV residual, phase scalar, reconstructed sum, and metadata role. Then pilot the primary route on:

- `c82s4`: high teacher residual; run UV-only polish.
- `c83s4`: low-but-failing transition contrast; run UV-only polish.
- `c82s5`: zero-load passing control; read-only reevaluation, no solve.

Freeze accepted damage, the correct prior, the original target trial-fatigue array, mesh, boundary conditions, active DOFs, material parameters, and `eta=0`; initialize from accepted UV and update UV only. Do not update damage or history, change residual stiffness, enable rescue logic, or change gates. Freeze the solver and iteration budget before execution. An independent residual assembly decides `rho_u <= 1e-3`.

Report pre/post UV residuals, both native components, box and hard-KKT results, displacement change, and active-driver change. Store original and polished arrays separately with an explicit parent link. The archived MATLAB-vector bridge applies only to the original accepted field, not automatically to the polished field. A UV pass with any other failed gate leaves `full_teacher = NOT_QUALIFIED`.

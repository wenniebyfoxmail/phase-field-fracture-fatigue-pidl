# S09-E009 core code review round 2 — 2026-10-17

## Verdict

`REVISE_AND_REREVIEW`

Haofan ChatGPT Pro reviewed exact commit
`d309c60278719b1d18ac07b96529a46211cd2b57` only against Round-1 findings
F1–F3. It independently reproduced 48 selected tests and ran 39 narrow
contract checks, of which three exposed the two residual issues below. No
optimiser step, producer access, or training occurred.

## Result

- **F3 closed.** Exact-zero and retained near-zero projection labels are
  truthful, and residues at `1e-14` and `1e-200` remain numerically present.
- **F1 partly closed.** Stable norms and most derived finite checks work, but
  replay still only checked the final merged vector. One objective with an
  overflowed raw norm could be silently zeroed by the inherited merger while
  the final direction remained finite.
- **F2 partly closed.** AUC counts and cycle IDs became native JSON types, but
  `safe_replay_ratio()` and `group_amplitude_ratio()` could still return a
  NumPy `float32` value.

The required repair is narrow: check finite raw norms and the normally finite
replay diagnostics at the frozen merger boundary, and convert accepted ratio
inputs/outputs to native Python floats. Preserve one replay merger call, one
clip, zero-denominator semantics, and every threshold.

The approved protocol and runner boundary were not reopened. A new exact
commit requires one more narrow core rereview before runner integration.

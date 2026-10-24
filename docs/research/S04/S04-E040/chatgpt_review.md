# S04-E040 — internal ChatGPT Pro design review receipt

**Channel:** ordinary ChatGPT Chat on the user's Haofan Pro account, Chat
mode. No file was attached.

**Date:** 2026-10-24

**Reviewed material:** `chatgpt_review_packet.md` from source commit
`722b57fd`.

**Conversation:** <https://chatgpt.com/c/6adbf811-efc8-8326-aa2e-650a44eb69aa>

## Verdict

**Approve with specific modifications.** The review found the state-referenced
feasible map coherent for the one fixed numerical benchmark. It did not require
an explicit projected damage subsolve or a different optimizer family.

It stated that the method is a feasible parameterisation on the declared support,
not a globally equivalent constrained damage solve. A completed run can support
only discrete feasibility and the declared RPROP completion condition; it cannot
by itself establish global optimality, FEM agreement, or physical validation.

## Required modifications and adoption

1. **Exact-start/reference consistency.** The review required an explicit
   check at initialization, every accepted commit, and save/reload that the
   accepted network reproduces `q_ref` and maps to accepted `h`; network,
   `h`, `A`, `psi_prev`, and `q_ref` must be committed atomically. E040 adopts
   a same-device/dtype/mesh-order `torch.equal` contract, which is stricter
   than the review's suggested declared floating-point tolerance.

2. **Stopping interpretation.** The review required the local loop to copy the
   standard relative-loss rule and distinguish scalar stopping from a claim of
   damage or field-space stationarity. E040 retains the standard ten-step,
   `5e-7` relative criterion and pre-cap requirement, then records inactive
   damage-branch fraction and physical-energy stall status as diagnostics. They
   are not additional optimization gates.

The review also confirmed that the direct runner-local objective and no-grad
shadow `E_irr` calculation correctly avoid the `0 * E_irr` graph shortcut;
that direct TRI3-GP checks remain useful implementation verification even though
linear interpolation transfers nodal bounds by convexity; and that the fixed
15-substep, seed-1, Umax=0.12 benchmark should remain unchanged.

## Review boundary

This is a non-binding design review. It does not certify code, execution,
numerical result, FEM agreement, or physical validity.

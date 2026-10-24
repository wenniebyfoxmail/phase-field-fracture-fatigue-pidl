# S04-E040 — internal ChatGPT Pro exact-source/contract review

**Review surface:** [ChatGPT review](https://chatgpt.com/c/6adbff10-5038-8330-8d40-99be48325d43)  
**Account verification:** the visible profile menu showed `haofan Pro`.  
**Visible review setting:** the model selector exposed thinking effort `Medium`
(`2 of 5`); it did not display a model name.  
**Reviewed source snapshot:** `5aaa317ed55175e80acb581d922eb6a1a4cb6d49`  
**Packet snapshot:** `7638135199f9c540eaee69e0266b9699976e692e`
(`chatgpt_exact_source_review_packet.md`), based on
`99339eedabe685a3d22912b700776e7ab881137d`.

## Scope supplied

The review received the fixed one-arm contract: the state-referenced
feasible-damage mapping, direct `log10(E_el + E_d) + 1e-5*L2` objective,
detached `E_irr` shadow diagnostic, exact reload equality, v2 hash-linked
accepted-state transaction, copied standard RPROP stopping, fixed time/update
budget, and accepted-prefix-only comparison against R001. It was expressly
asked not to certify source code, execution, FEM agreement, or physics.

## Response

The reviewer found **no concrete P0/P1 design or contract blocker** and judged
the one bounded numerical run adequately specified at that level. It found the
selected right derivative `(1-h)/4` at the kink internally consistent with the
CUDA guard; the direct objective sufficient to exclude `E_irr` from backward
propagation; the pointer-authoritative recursive chain coherent for restart;
and the analyzer unable to accept an unpublished staged step.

The review explicitly retained the limits of that conclusion: it did not
independently reproduce tests, certify the exact source, execution, numerical
convergence, field-space stationarity, global optimality, FEM agreement, or
physical validity. Exact-source review is recorded separately in the
independent Code Ready audit for `5aaa317e`.

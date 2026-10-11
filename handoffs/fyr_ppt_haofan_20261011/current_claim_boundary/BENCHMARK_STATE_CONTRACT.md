# Benchmark and state reporting contract

Date: 2026-09-29. Scope: reporting correction of existing evidence, not a new experiment or a passed solver-equivalence gate.

## Authority and roles

`benchmark_event_contract.csv` records the existing manifest and monitor evidence. For Umax=0.12, canonical FEM means Hard-5 eta0 native-Q4, first detect c83, confirmation c86. The historical eight-step reference is c86 first detect/c89 confirmation. Its first-detection evidence includes checkpoint/code inference; do not upgrade it to a retained original console observation. PIDL is first detect step444=c89 peak, confirmation step447=c90 within-cycle substep; the three-step delay is not three physical cycles.

PIDL mapping: recovery raw step=0; cyclic substep q in {1,...,5} has raw step 1+5*(c-1)+(q-1). Peak q=4; unloaded q=5. Step447 is c90/q2, NOT c92 and NOT a peak.

Do not compare confirmed FEM terminal time with PIDL first detection. Keep source-reported first detection separate from any future re-evaluation at a common peak, threshold, node-count and connectivity rule. This correction does not certify exact event-detector equivalence across implementations.

## Required state key

Every field row must name: physical family, trajectory identity, solver/commit, initial preparation, Umax/loading schedule, cycle, substep/phase, pre/post-update timing, native support and spatial reduction, field channel, and reference identity. Unknown fields stay UNKNOWN, not inferred from a matching cycle number.

Same-cycle, own-first-event, and own-confirmed-terminal comparisons are different estimands. Store the comparison type explicitly. Never align using the true future event as a predictive input.

## Force and state semantics

FEM boundary reaction is a directly exported solver quantity. PIDL 2E_el/Umax is an energy-derived proxy, not a reaction export. Kt is not boundary force. Peak energy cannot silently share a state label with unloaded displacement or a later refreshed history. A visible binary crack, diffuse damage, accumulated fatigue history and fatigue degradation are distinct variables.

## Current manuscript treatment

Local Chapters 3/4 now separate canonical Hard-5 event reporting from retained historical eight-step-FEM/five-step-PIDL field diagnostics. Historical numerical values and figures are retained with explicit captions; no old field plot was relabelled or recomputed as Hard-5. Chapter 5 no longer turns an unclosed numerical comparison into proof that physics-only supervision is intrinsically insufficient.

Still outstanding: regenerate matched-phase native-support field comparisons from canonical archives if they are to carry the main solver-mechanism claim. The source data and algorithms are unchanged.

## Legacy notes

Old frontier, monitor and decision statements remain archival evidence. This contract supersedes their c89=c89 event-agreement wording for current reporting. It does not retrospectively change old protocols, verdicts, runs, or figures.

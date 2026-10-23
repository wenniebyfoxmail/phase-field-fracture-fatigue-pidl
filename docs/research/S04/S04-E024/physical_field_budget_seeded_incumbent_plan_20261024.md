# E024-D014: seeded feasible incumbent and retention plan

## Purpose

Repair the D013 finite-solver failure mode without weakening the physical-field contract. The repair makes a previously verified, strictly feasible raw head available as the starting incumbent, then preserves it if the local proxy cannot return a new feasible direction.

## Immutable pairing and centre

Each of c20s4, c60s4 and c83s4 keeps its own E023 joint-training output head as `theta0`. All FEM errors, the 13 guard ceilings, four field-change denominators, Q, geometry, masks, BC, compact window, producer D, features, reference, damage, history and fatigue remain tied to that E023 state. The saved D012 head is a pinned comparator and candidate seed only.

## Seed qualification

Before any profile solve, the runner casts the saved head to the producer dtype/layout, reconstructs it through the raw frozen network path, and performs the same identity and realization checks used for a finite candidate. It evaluates the actual field against all 13 guards and Q around `theta0`.

The seed is eligible only when all 13 guards are no worse than E023 and `Q <= .1`. This strict qualification is shared by all four profiles, including the seven-guard diagnostic. It prevents the diagnostic row from importing an unprotected background regression.

The selected initial incumbent is the lower deterministic key among E023 and an eligible seed:

`(actual full-UV squared error, Q, source priority, quantized-head SHA256)`.

E023 wins ties. The saved seed therefore cannot replace E023 merely because it exists. The seed qualification, source archive/hash, quantized-head digest, actual report, failures and selection key are written once per state and copied into each profile's first `initialization` event.

## Local search and retention

The existing full-head proxy remains a single zero-increment SLSQP solve with the existing physical constraints, radius and ordered nine finite halvings. It is rebuilt at the current actual incumbent. A trial remains accepted only if the quantized raw field passes the profile's guard policy and Q, has positive actual and predicted UV reduction relative to the current incumbent, and meets the existing agreement rule.

An accepted trial replaces the incumbent only after its actual reconstruction passes. A rejected trial never changes it. If the solver returns no proxy-feasible step, all nine finite trials are rejected, or the finite relinearization limit is reached, the last actual-feasible incumbent is retained. The runner records this separately from `accepted_steps`: seed adoption is not a new optimization step or a newly discovered correction.

The initial incumbent must be replayed before the first solver event. Replaying recomputes seed qualification from pinned data and rejects any altered source identity, qualification record, selected head, centre, or final trajectory.

## Computation and authority

This implementation task runs only an artificial, no-model/no-FEM synthetic check. It does not execute the three states, solve a real proxy, reconstruct a real candidate, train, send files, use remote hardware, or change frozen history/fatigue. A future D014 run remains a separate request requiring its own bound execution package and explicit approval.

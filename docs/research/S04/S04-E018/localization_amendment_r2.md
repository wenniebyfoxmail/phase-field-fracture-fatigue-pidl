# E018 geometry amendment proposal 2026-10-12 r2

No E018 producer run has started. Preserve r1 planning/code review and source.
The actual-state offline geometry preflight (no training/no UV-error-based patch
selection) found that the all-damage rectangle covers0.5354 domain mass at
c60/c83 because of tiny disconnected right-bottom damage islands. It covers
only0.04124 at c20. This changes the intended localization strength by state.

Proposed repair: use the Q4 EDGE graph on nodes with damage>.1. Edges are Q4
consecutive node pairs0-1,1-2,2-3,3-0; no diagonal connectivity. Identify all
connected components. Exactly one component must contain a node with x=-.5
and abs(y)<=.02 (the fixed initial-notch anchor). If zero or multiple components
satisfy this condition, fail validity; no largest-component or target-based
fallback. Use this component's bounding rectangle with the SAME .02 padding,
C2 window, local coordinates and8x283 paired branches. Its selection uses own
same-state xy/damage/conn only. Record all component masses/counts/bounds,
anchor component identity, excluded island mass and support/background mass.

All damage nodes, including excluded islands, remain in stratumA, loss,
full-field primary criterion, conditional region metrics and final Q4 diagnostics.
The global branch remains active on islands. Only the local branch support
changes. Do not clip damage, drop a state/node, use UV residuals for selection,
or alter the sampleralpha.7, optimizer10000 budget, primary<=.001 or control.

Actual component findings:
- c20: one anchor component4082 nodes; no exclusion.
- c60: anchor5710 nodes, mass.0225476; island6 nodes, mass1.2850e-5.
- c83: anchor7217 nodes, mass.0284509; island8 nodes, mass2.0758e-5.

This is a target-independent preparation repair, not evidence that localization
will improve fit or that the islands are FEM mistakes. New protocol revision
20261012-r2-anchor-global-local-screen requires revised planning and exact-commit
Code Ready review; r1 CODE READY cannot authorize this changed geometry.
E017 remains unchanged and proceeds independently.

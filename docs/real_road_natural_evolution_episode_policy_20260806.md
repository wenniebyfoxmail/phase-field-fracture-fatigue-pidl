# Real-road natural-evolution episode policy

Date: 2026-08-06

Status: `CURRENT_PROJECT_RULE`

## Purpose

This rule applies whenever a research track claims to model the natural
development of cracks or deterioration between repeated real-road
observations. Maintenance does not need to be a model predictor in such a
track. It must, however, be used to define episode boundaries so an
intervention is not silently interpreted as natural evolution.

An intervention-response or maintenance-utility study is a different research
task and requires its own track and preregistration.

## Episode definition

A source-to-target transition is eligible for a natural-evolution episode only
when all of the following are established from metadata frozen before outcome
fitting:

1. Source and target refer to the same physical asset, registered panel, lane,
   and coordinate frame.
2. Source and target belong to the same construction or structural regime.
3. No documented maintenance, rehabilitation, reconstruction, overlay,
   milling, sealing, patching, or other state-reset event occurs in
   `(source_time, target_time]`.
4. No section closure, Out-of-Study date, sensor termination, or other terminal
   censoring boundary occurs before the target observation.
5. The target is an actual qualified observation, not an interpolated state or
   a value reconstructed across a reset.

At a reset, the pre-event episode ends. A post-event observation may start a
new episode only when its post-intervention identity, construction regime, and
registration are qualified. State from the old episode must not be propagated
through the reset.

## Required handling

- In a natural-evolution track, maintenance/reset metadata is an eligibility
  and censoring channel, not a default prediction feature.
- Freeze one episode manifest before fitting. It must name every included
  transition and every exclusion/review reason, with event source and hashes.
- Perform eligibility using event/construction/observation metadata only.
  Never infer maintenance from a negative crack change and then delete the row.
- Ambiguous event timing, unknown construction identity, missing timeline, or
  unresolved registration is `REVIEW_OR_QUARANTINE`, not an automatic pass.
- Absence of an event in an available record supports the wording
  `no documented intervention`; it does not prove that no unrecorded work
  occurred.
- Do not keep deleting complete cases after the row set is frozen. A later
  exception must trigger the track's declared fail-closed or amendment route.

## Claim boundary and legacy results

Passing this gate authorizes only a natural-evolution dataset description. It
does not establish that maintenance never occurred, that observed crack change
is purely physical, or that a model is predictive or causal.

This policy is prospective. A previously sealed experiment remains valid under
its own frozen protocol and disclosures; it is not silently re-scored or
rewritten. Reuse of its rows in a new track must pass this policy anew.

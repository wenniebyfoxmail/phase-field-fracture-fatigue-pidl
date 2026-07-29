# Agent2 handoff: trajectory readiness inputs

Agent3 has frozen its consumer protocol but has not inferred the producer
schema. Please publish one signed task2 package containing:

1. a versioned trajectory bundle contract with schema id and file SHA256;
2. four bundle records for hard/soft initial tip x 5/8-step loading history;
3. per-bundle path, SHA256 and mechanism-completeness verdict;
4. stable trajectory id and independence group for each complete combination;
5. exact state/observation/scenario registries and event-phase provenance;
6. coverage flags for same-regime h1-h3, transition warning and reset
   propagation;
7. a signed leave-one-combination-out split keeping all cycles and resets from
   the held-out combination outside normalization and training;
8. uncertainty eligibility and event/right-censor status without filling
   unavailable values.

The four normalized independence-group ids are pre-registered as
`hard_tip__5step`, `hard_tip__8step`, `soft_tip__5step` and
`soft_tip__8step`. The Agent3 readiness gate requires this exact set and an
explicit frozen/verified split flag; four arbitrary bundles cannot open it.

The evidence scope must be labelled within-Hard5 factorial numerical
trajectories. Do not label the four combinations as independent roads or as
geometry/material generalisation.

After publication, Agent3 will add one schema-specific adapter, verify every
hash, rerun the readiness report and seek an explicit launch decision. It will
not start training automatically.

# External plan review — open-data phase-field inverse-to-prediction

**Review date:** 2026-10-08  
**External reviewer:** independent ChatGPT review, conversation `6ac787b9-5b04-8333-a526-15f70563050a`  
**Verdict:** `REVISE`

The reviewer accepted the scientific order—first test whether observable
mechanics add predictive information beyond matched geometry-plus-load, and
only then test a phase-field representation—but blocked launch under the
original protocol.

Mandatory revisions:

1. treat complete acquisition episodes, not individual DIC files or load-state
   images, as independent observations;
2. replace file-count `60/20/20` with causal physical-cycle cuts and purge every
   origin/target pair crossing a partition boundary;
3. prove that a fixed-cycle future crack-length target exists without
   whole-trajectory interpolation;
4. give the geometry and mechanics models identical crack-length/history/load
   information, with only one frozen mechanics package differing;
5. use one physical-cycle horizon and paired CRPS as the eventual primary
   estimand; choose one augmented package before opening the sealed suffix;
6. prohibit constitutive, fracture, and fatigue parameter inversion in Gate 1;
7. require a second preregistered comparison against the successful
   observation-only mechanics model before claiming phase-field utility;
8. make CARPIUC an optional, bounded tooling check rather than a mandatory
   scientific gate.

The review proposed a 10% reduction in sealed-future mean CRPS as a practical
progression threshold. Local adjudication retains this only as a candidate
freeze item; it is not an evidence-derived constant and is not authorised until
the value-blinded audit establishes evaluation resolution and a later reviewed
forecast protocol freezes the threshold.

Allowed outcome boundary:

- a Gate 1 pass would establish only incremental predictive utility of the
  specified mechanics observation package for one horizon, specimen, and
  acquisition policy;
- it would not establish unique phase-field recovery, material truth,
  population generalisation, road transfer, or deployment;
- a Gate 1 fail would reject only the frozen package and procedure;
- an audit failure means the dataset cannot adjudicate the question.

Local decision: conduct the AA2024 value-blinded qualification audit first. Do
not train, invert parameters, or inspect sealed future crack-growth values.


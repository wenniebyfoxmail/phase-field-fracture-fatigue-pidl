# Thesis main line and three research questions — discussion draft

Date: 2026-09-29. User priority: graduation/thesis first; ZP04 is sidework. Deadline, publication requirement and doctoral year: UNKNOWN pending user response. This is a thesis architecture proposal, not an approved experimental protocol, novelty certificate or guarantee of degree sufficiency.

## Main question

Under partial observations, what state information is sufficient to predict fatigue-crack evolution and critical transitions, and when can those predictions be trusted?

Working title: State information and reliable prediction of fatigue-crack evolution under partial observations.

One material/loading family is the minimum scientific scope. Real-road transfer is a conditional extension, not a prerequisite for every chapter. The mechanics surrogate's full hidden states are legitimate inputs only for the known-state numerical question; they are not operational road observations.

## Three scientific chapters

| Question | Scientific distinction | Existing evidence | Missing decisive evidence | Minimum defensible output | Handoff |
|---|---|---|---|---|---|
| Q1: What information is sufficient for future evolution? | Geometry, diffuse state and history can differ even when scalar responses agree; distinguish solver error from state insufficiency | PIDL/FEM discrepancies; full-damage conditioning; failed mask/reaction reconstruction | Same observation/known future forcing but different admissible states with different future outcomes, across more than one development trajectory; numerical qualification | Tested state-information hierarchy and bounded non-identifiability/ambiguity result | Specify which state channels Q2 receives and what Q3 must observe |
| Q2: Can a known-state predictor capture the critical transition? | Accurate routine propagation is distinct from autonomous transition prediction | Existing secant, Markov/TCN/Transformer and operator diagnostics; transition failures | Entire physically varied simulation cases held out, fixed forecast origins and horizons; comparable numerical teacher | Transition-aware prediction or a quantitative map of failure, compared to strongest simple control | Fix the propagator and its approximation error for Q3 |
| Q3: Which limited observations restore useful, calibrated forecasts? | State reconstruction and forecast utility differ; point accuracy and uncertainty differ | Single-trajectory sequential/sparse energetic assimilation; uncertainty undercoverage | Budget-matched observable comparisons with realistic operators/noise and held-out cases; separately calibrated uncertainty | Observation-value versus cost/noise curve and validity domain of forecasts | Thesis synthesis: when to predict, update or abstain |

Q1 is not a solver benchmark alone, Q2 is not another inverse problem, and Q3 must produce an observation/reliability contribution rather than merely wiring Q1 and Q2 together. A negative result is only chapter-quality if it discriminates alternatives and establishes a reproducible boundary; one failed network is insufficient.

## Avoid a serial failure chain

Q2 can start with legitimate full current-state inputs from a qualified numerical reference, whether or not Q1 finds a unique observable inverse. Q3 can use a qualified deterministic solver or transparent propagator if the neural operator fails. Q3 can infer a distribution of predictively equivalent states rather than demand unique material parameters and full fields. No chapter must promise identification of damage, history, material and unknown loading simultaneously.

## Existing FYR crosswalk

Chapters 1–2: narrow context/gap to the selected material and prediction target; road motivation remains bounded.
Chapter 3: shared model, numerical qualification and state/observable definitions.
Chapter 4: current PIDL diagnosis motivates Q1, with historical/canonical reference separation.
Current Chapter 5 WP1/WP2/WP3: retain as historical proposal; proposed final-thesis chapters become Q1 sufficiency, Q2 transition prediction, Q3 observation-conditioned reliability. The rewritten final programme requires supervisor choice before replacing all FYR planning prose.
Final synthesis: distinguish what information matters, whether it can be propagated, and whether it can be observed reliably. ZP04 is separate sidework, not forced into this causal chain.

## Immediate discriminator, using existing evidence first

Current numerical PIDL already has prescribed material/loading and state-update equations: its failure cannot be attributed automatically to missing real-world sensors. First separate (A) inconsistent numerical/protocol implementation, (B) optimisation/representation error, (C) insufficient state representation for a learned transition. Existing oracle and assimilation results address conditional continuation, not all three causes.

Re-use the four decisions dated 2026-07-16/18 listed in EVIDENCE_REUSE.md; do not repeat mask+reaction, one-ring GNN or sparse raw-energy assimilation as untried ideas. Their eight-step c86/c87/c89 states retain that trajectory identity. They are not new Hard-5 c83/c84/c86 results.

The next scientific proposal should compare candidate states that are indistinguishable under a declared observation operator and known forcing, then test whether their futures differ beyond numerical/measurement error. This is a candidate discriminator, not a frozen design. Existing-case matching is exploratory and must not become a claimed untouched test. If archived cases lack the requisite variation, prepare one bounded prospective numerical design rather than another architecture sweep. Formal masks, thresholds, models and producer jobs require a reviewed protocol; no new experiment is approved here.

## Data independence and holdouts

Use INDEPENDENCE_LEDGER.csv. Four factorial cases and three cross-Umax cases overlap at Hard5 U0.12: at most six unique candidate numerical trajectories, pending native provenance reconciliation. They remain one geometry/material family, not six physical specimens. Seeds and frames are nested technical observations.

Previously inspected paths stay development data. Hold out complete future numerical parameter/loading families before analysing outcomes. Number of independent cases is selected from the intended claim, event occurrence and precision, not an arbitrary universal quota. A small bounded design can test a numerical mechanism; it cannot establish road-scale generalisation.

For road observations, first fix ONE target (e.g. registered crack-length increment over a fixed interval), identity, measurement uncertainty and intervention/censoring. Do not require an entire multimodal world-model dataset. Existing LTPP spatial registration and annotation status require fresh task-specific qualification; 37 annotated states must not be declared 37 metrically registered prediction targets.

## Completion gates and work sequence

Days 1–7: reporting contract plus reused-evidence matrix; identify the primary claim and one unresolved discriminator; no architecture sweep. Deliverable: supervisor-readable 2-page programme and one evidence-gap table.
Days 8–30: freeze one numerical family, baseline and forecast target; qualify references and choose the bounded independent test design before outcomes. Deliverable: one formal reviewed protocol and a verified source/holdout inventory, or an explicit no-go reason.
Days 31–90: execute only the named approved discriminator, write Q1 result and decide whether Q2 model work is justified. Q3 observation planning can proceed independently. One primary branch, with no more than a maintenance time budget for ZP04.

Capacity is provisional until deadline is known: main line 80–90%, sidework 10–20%. Do not convert this into a degree-compliance claim. If thesis submission is near, reuse validated studies and narrow the scope instead of promising field deployment and three new model papers.

# AT1-fatigue mesh-PINO framework review

**Date:** 2026-08-24  
**Review class:** independent frontier coding-model review used because a GPT Pro endpoint was not available in this session  
**Scope:** planning and state/provenance audit only; no training authorization

## Main challenge

Do not begin with a raster FNO plus a generic PDE penalty. The defensible first
candidate is a native-mesh node/cell operator whose physics residual is assembled
with the locked Q4 finite-element discretization.

The decisive prerequisite is whether the retained archive contains the true
Markov state and the unload/reload path required by the Carrara fatigue update.
Cycle-peak differences cannot be presumed to equal the accumulated within-cycle
history increment. If those states are absent, the route must stop or be renamed
as an equilibrium/phase-field physics-guided operator rather than a full
AT1-fatigue PINO.

## Advice adopted

- Audit residual computability before writing or training the operator.
- Require coherent nodal displacement and damage plus Gauss-point committed
  history and fatigue variables at every retained load substep.
- Derive raw/active energy and degradation from the predicted independent state;
  do not independently predict four mutually constrainable output channels.
- Compare physics-on and data-only continuations of the same native-mesh model
  before comparing against PIDL.
- Preserve whole-trajectory holdouts and the within-Hard5 numerical claim scope.

## Advice deferred

- Architecture implementation, physics-weight selection, and training are not
  authorized by Stage 0.
- FNO is deferred until a conservative mesh-to-grid projection audit exists.
- A complete producer export is deferred until a small residual-validation packet
  proves that the locked residual evaluator can reproduce FEM states.

## Stop rule

If the archived FEM truth cannot be evaluated with the producer-matched
equilibrium, projected-KKT, and fatigue-history residuals, do not launch a PINO
run and do not tune residual weights around the missing state.

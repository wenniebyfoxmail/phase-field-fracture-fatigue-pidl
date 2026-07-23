# Road time and inspection-trigger task brief

## Mechanism question

How should a road-facing fracture digital twin map simulation time to traffic,
environment, calendar time, and inspection epochs; how far may it propagate a
recent assimilated state; and when should it stop recursion and request image,
FWD, or strain observations?

## Claim change

The result may support a road-time/interface formulation and a single-trajectory
trigger diagnostic. It may not support road early-warning generalisation, a
conversion from one FEM cycle to one axle/ESAL/calendar interval, or autonomous
prediction of the c87/c89 regime transition.

## Cheaper diagnostic

Reuse the frozen 18 matched temporal prediction assets and existing eta0 FEM
audit dataset. Do not train a new model.

## Minimal assets

- road-time mapping specification;
- short- versus long-horizon specification;
- Agent1-compatible observation-trigger specification;
- trigger trajectory CSV and figure;
- short-to-long/RUL schematic;
- decision note and manifest.

## Frozen analysis rule

Fit model-only signal envelopes on c77-c79. Trigger decisions use only ensemble
disagreement and predicted-state/support drift. Open c80-c89 only for subsequent
diagnostic application. FEM-centred columns are labelled `audit_only_*` and are
never read by the trigger rule.

External GPT Pro review was not available in this execution surface. The user
provided and approved the task design; all numerical trigger thresholds remain
quarantined pending independent review and physically diverse calibration.

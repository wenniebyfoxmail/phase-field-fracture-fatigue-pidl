# Observation-Innovation Trigger: Stage-2 Decision

## Verdict

**Road-like image innovation remains late; positive lead appears only with an oracle-derived localization proxy.**

The stage-1 model-only policy first requests an inspection at step `83` and stops recursion at `84`. With only the synthetic crack-image geometry channel, the same frozen policy first requests and stops at step `81`. With image plus the oracle-derived raw-energy localization proxy, it first requests and stops at step `80`. The independently joined FEM audit first falls below the absolute-p99 support gate at step `81`.

Therefore the model-only request has lead `-2` (a lag when negative), and image-only has lead `0`. The `+1` lead appears only after adding the hidden raw-energy localization proxy. The reality-facing result is therefore **negative**: the available road-like image proxy does not provide positive lead. The oracle-assisted result is an upper-bound diagnostic, not evidence of road early warning, and it has no road-time/ESAL/calendar conversion.

## What the trigger actually consumed

- model ensemble/self-state diagnostics from the matched model committee;
- a declared synthetic crack-image geometry innovation;
- an explicitly labelled oracle-derived raw-energy localization proxy;
- no FWD innovation, because the archive contains no displacement or FWD basin response;
- no traffic/environment OOD, overdue, maintenance, or sensor-quality event, because those streams are absent.

The runtime decision function receives none of the FEM IoU/error columns. FEM support is joined afterwards under `audit_only_*`. Automated tests reject extra FEM/audit/failure keys and show that changing audit values cannot change decisions.

## Frozen rule and false alarms

The feature envelopes were frozen from c77-c79, using the inherited robust warning/hard thresholds `z=3/5`. c80-c89 were not used to fit thresholds, and no threshold sweep was performed. Under the predeclared three-step association rule, the descriptive false-alarm counts are `0`, `0`, and `0` for model-only, image-only, and oracle-assisted policies. A false-alarm **rate cannot be estimated** from one trajectory and one hidden support transition.

## Reality gap

1. The image channel needs registered repeated road imagery, segmentation calibration, visibility/missingness, and registration uncertainty.
2. FWD requires measured basins plus a calibrated structural response operator, layer/support conditions, load, and temperature.
3. Strain localization requires synchronized sensors or DIC and a calibrated projection/error model. The present raw-energy proxy is not strain.
4. WIM/load spectra, timestamps, temperature, moisture, maintenance, inspection policy, and sensor drift are absent.
5. Thresholds require physically independent calibration trajectories and leave-one-road-section/asset-out validation.

## Decision

Accept `observation_innovation_packet_v1` and the leakage firewall as an interface/framework diagnostic. Record image-only triggering as a negative result and quarantine the oracle-assisted positive one-step lead. Do not claim real-road detection performance, false-alarm rate, or RUL improvement from this package.

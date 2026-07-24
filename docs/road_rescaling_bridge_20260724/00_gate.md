# Road Rescaling Pre-Launch Gate

1. **Mechanism question**: can the formal toy problem be mapped to dimensional
   systems without changing its governing dimensionless groups, and which
   additional groups prevent that mapping from being called a road model?
2. **Claim changed**: a pass supports only code-level dimensional similarity;
   a fail would invalidate the present physical-unit conversion. Neither result
   establishes road calibration or forecasting skill.
3. **Cheaper diagnostic**: yes. Audit the energy implementation and calculate
   the dimensionless vector before any FEM or PIDL training.
4. **Minimal asset**: one comparison CSV, one sensitivity CSV, one observation
   map, one figure, and this decision package.
5. **Registry path**: add one diagnostic entry to
   `docs/pidl_experiment_inventory.md`; any later producer run must be a new,
   separately gated attempt.

No training run is approved by this attempt.

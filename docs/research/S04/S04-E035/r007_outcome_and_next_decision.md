# Shear result and next decision

The installed FEM has clamped notched shear, simple-plate shear, tension,
three-point bending, and X/Y displacement/traction primitives for mixed loading.
These are different geometries/support/model configurations, not interchangeable
switches. See the verified inventory in [experiment.md](experiment.md).
Compression/cyclic sign reversal does not establish crack-contact/friction or
qualified fatigue physics.

The chosen first comparison remains normalized AT1/AMOR clamped monotonic shear:
bottom fixed, top ux=U/uy=0, sides free; common material, original diffuse notch,
251fixed alpha1nodes and30prescribedU. FEM Q4/PIDL child-T3 quadrature and
recovery differences remain explicit. PIDL boundary/trial-space adjustment is
prepared; no FEM field labels enter its fitting.

R007 gives an independently verified12-state prefix U=.03–.28, extending R006's
six states. It does not give the requested complete paired comparison. AtU=.29,
78completed coupled staggers leave printedresidual.00023059; unaccepted damage
crosses1.005 afterstagger51 and reaches1.0060855on3nodes. FinalfreshPFresidual
is missing. The600s stop and status-report defect are preserved in [R007](runs/S04-E035-R007.md).

Next design should first explain the coupled mechanics–phase-field iteration
and damage overshoot under the unchanged physical contract. Use the retained
per-stagger alpha, residual/energy and native phase-recovery sources to determine
whether a bounded outer-iteration acceleration is appropriate. Larger inner
Newton limits are unsupported: the remaining obstruction appears after inner
mechanical solves; more wall time alone has not been shown to satisfy both
coupled residual and damage bounds. No clipping, tolerance relaxation, load
subdivision, new algorithm or new scientific attempt is authorised here.

Two local reporting repairs are prepared: clear success on observer exceptions,
and read the live nested equation counter. The added11tharrayfixture has not
executed inMATLAB; the frozen run passed its original10fixtures. A future
approved producer must execute the full repaired fixture set before science.

Once a complete valid FEM trajectory exists and GPU0 is explicitly released,
run the already aligned independent PIDL under a newly confirmed bounded window.
Compare matchedU direct reactions, displacement/damage fields and energies;
retain every candidate and report numerical validity/coverage. The primary
damage error remains the declared area-weighted trajectory mean, with Q4/T3
reduction differences retained. No training, partial-prefix substitute or retry
is enabled by this plan. This is a synthetic numerical comparison, not physical
or road validation.

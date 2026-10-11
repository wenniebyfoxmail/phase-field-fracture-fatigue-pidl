# Forecast-design handoff after structural admission

Status: design input only; no table export, task qualification or training.

The 342-stage sequence passed cycle/date header admission. Output contains
114 distinct cycles and 114 distinct crack-length values; joint grouping and
independent units are not established. Time has two decreases; its physical
meaning remains unknown.

## Smallest next scope

1. Confirm released specimen identity, loading protocol, units and the meaning
   of cycle/cracklength fields from auditable metadata. Keep unresolved items
   explicit. Identify whether field values are measured, interpolated or reused.
2. Export a bounded scalar-only stage table with exact stage identity, cycle,
   acquisition-relative date, cracklength and relevant loading values. Do not
   read numerical DIC/connection bodies for the initial scalar task. Bind the
   table to the same archive and reviewed parser.
3. Determine exact cycle ties, joint-label agreement and acquisition order.
   Report group counts and discordant groups; do not silently average/drop
   duplicates. Keep each verified tie group wholly within a split. Repeated
   snapshots are not independent specimens.
4. Before accessing confirmation target labels, freeze a chronological grouping
   and target policy. A cheapest candidate is next positive-cycle acquisition
   prediction, conditional on its recorded cycle gap, explicitly a retrospective
   recorded-acquisition task. It is not arbitrary future-time forecasting.
   Information available at origin: prior admitted readings and known target
   gap only. Prevent future labels/geometry from affecting origin features.
5. Evaluate persistence and a past-only secant baseline before adding a learned
   model. Require positive past cycle spacing for secant; freeze handling of
   unavailable spacing and missing labels. Split/grouping and metrics need an
   exact reviewed task contract before scored execution.

No train/dev/holdout sizes or error thresholds are selected from unexported
data. First quantify usable positive-cycle transitions and measurement noise;
then calibrate a meaningful primary comparison. Keep fit, prediction and
physical interpretation separate. A scalar forecasting benchmark can advance
observation-to-transition work but does not yield a phase-field state or unique
material properties without additional mechanics/observation identification.

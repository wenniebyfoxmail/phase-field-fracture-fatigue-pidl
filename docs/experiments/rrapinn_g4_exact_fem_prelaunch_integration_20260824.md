# RRaPINN G4 exact-FEM prelaunch integration — 2026-08-24

## Decision

`PASS_EXACT_INPUT_AND_ANALYZER_INTEGRATION; TRAINING_UNAUTHORIZED`.

The v2.1 U0.12 native-Q4 package closes the external FEM input blocker. It does
not establish RRaPINN efficacy and does not authorize Taobo launch.

## Frozen evidence

- 20/20 package SHA256 records pass, including c76/c82/c83 exact-peak states.
- Q4 geometry has 86,408 elements, 86,756 nodes, positive areas and unit total
  area.
- first-detect selected-cycle counts are 0/0/22; c83 is truth from the
  hash-locked historical-reference receipt. c86 is confirmation only.
- contained projector v2 has 85,113 headline rows and excludes 1,295 fallback
  rows. One assignment differs from v1, so v1 is superseded for v2.1.
- blind analysis computes 72 rows across two opaque arms: residual tails,
  field tails/support/error, damage morphology and first-detect.

## Morphology decision

The contained exact-Q4 domain is not elementwise mirror-closed: only 32.65% of
rows form mutual nearest reflected neighbours. Elementwise matching is
therefore rejected. The frozen alternative bins the contained domain into a
64x64 square grid, area-averages the field, reflects about `y=0`, weights each
pair by its lesser occupied area and fails below 50% paired-area coverage. The
exact input gives 51.9323% coverage and a constant-field asymmetry of zero.

Damage IoU is reported at 0.25/0.5/0.75. At threshold 0.25, four-neighbour
components, crack-tip x, centroid, forward extent, width and one-sided support
are also reported.

## Launch boundary

The launcher must verify, before creating output or calling training:

1. clean producer checkout at the lock-bound integration commit;
2. immutable prelaunch-lock SHA and every locked code/artifact hash;
3. a separate exact user-authorization receipt for only A/B U0.12;
4. no held-out U0.13/U0.11 access.

Next: commit and push integration, generate the immutable lock from that clean
commit, then run a fresh independent launch gate. No producer run is launched
by this integration.

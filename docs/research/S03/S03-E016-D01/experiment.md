# S03-E016-D01 — edge-method crosscheck and local/view variability

2026-10-13; S03; protocol `development-v1`. Controlled-experiment offline
diagnostic, NOT independent-reference metrology validation. User confirmed no
human crack-edge annotations exist. No independent reviewer/annotator has yet
qualified these image boundaries. Code/evidence independent review pending;
this protocol authorises an offline diagnostic and blind-reference preparation,
NOT formal Code/Evidence Ready or an expanded scientific claim.

Owner E016-D01; matching clean worktree/branch `codex/crackmnist-tokenizer-mvp`,
base `254ccd868f39640eadd18f03368267072cd91712`. New runner/protocol, compact
results, S03 dated impact and existing Obsidian milestones only. E015 unchanged.

## Frozen diagnostic contract

Question: which parts of the E015 crack-local signal survive a distinct edge
definition, a small measurement-location change and real repeat views?
Unit: three beams, 12 origin-fixed transects each; pixels/views NOT independent
specimens. Source D01 v4 DOI 10.17632/z3yc9z84tk.4. Same 14 fixed stages and
18 moving images at the low/high nominal load-stop groups from E006/E010.
Verify recorded CRC/size. No download, new image registration or training.

1. Alternate edge operator: use the E015 stored native grayscale profiles,
   smooth ONLY for derivative computation (sigma=1 native pixel), locate the
   darkest point within +/-15 pixels and strongest inward/outward gradient
   within 35 pixels of it. Gradient signs and >=2 gray/pixel are diagnostic
   detection checks; report censoring/coverage. No E015 half-depth edges/widths
   supplied to alternate operator. The paired edge-location/width discrepancy
   is METHOD AGREEMENT, not error against a reference. ID 6 first/last of every
   beam displayed irrespective of agreement; every profile included in tables.
2. Location sensitivity: resample native images with centers +/-2 native
   pixels tangent and +/-2 normal; algorithm, normal, stage mapping unchanged.
   Centered replays must reproduce E015 measurements before interpretation.
   Four coherent displacement trajectories, ALL 14 states/8 origins and
   same persistence/secant/half-secant rules. Report missing observations and
   matched-arm forecast support. No best-variant selection or threshold tuning.
   Report positive median stage changes and first-to-last growth across
   coherent variants. Also worst-case first/last envelope when displacement
   may differ by stage. Sensitivity is NOT repeated-acquisition accuracy.
3. Real same-stop view variability: replay all E010 transforms into FIRST
   fixed-frame native coordinates, using inverse(H_first)*H_view and separate
   native pixel-center resize maps for source/canonical shapes. 2 stops x
   (1 fixed+3 moving) x 12 transects x 3 beams = 288 opportunities. Leave out
   unsupported/censored/low-contrast profiles with explicit denominator;
   never zero-fill or substitute a different crack. Compare moving widths
   against the SAME-route fixed measurement for that stop; also record
   E010-route vs E012-route fixed discrepancies. Report view range/median
   absolute disagreement and common 4-view support. These are images grouped
   at nominal load holds, NOT hard-synchronised unchanged-state replicates:
   pose, registration, resolution, visibility and possible within-hold change
   are confounded. Call this repeat-VIEW variability, not pure metrology noise.
4. Human-reference preparation: anonymous fixed first/last crops, transect IDs
   3,6,9,12 per beam (24 unique tasks); repeated copies of six tasks under
   different IDs (30 task views), shuffled with seed=1613. No beam/stage labels,
   widths, profiles or algorithm edges in public packet; opaque local private
   key excluded from Git. Sample strip native canonical pixels, five parallel
   lines visible with ONE central measurement row. Annotator clicks visible
   left/right dark-crack boundaries and lower/upper plausible intervals, or
   flags occlusion/branch/spall/uncertain; not forced to trace shadow as truth.
   No automated candidate prefill. Annotator id and whether prior algorithm
   plots were seen must be recorded. Independent reviewer not yet assigned.

## Interpretation, budget and next lever

No defensible independent reference tolerance yet, so no physical pass/fail
threshold. Smallest evidence is paired operators + location/view spread on the
same units and human packet state. If alternate edges disagree or view
variability dominates stage increments, local correspondence/boundary reference
is the controlling bottleneck; do not expand networks. If coherent shifted
trajectories retain baseline advantage, preserve that component finding while
blocking absolute width/field/generalisation claims. E015 52.4% development
result is immutable and not "rescued" by a selected subset here.

Budget one offline run, no parameter sweep/extra data/model. Stop on CRC/identity
mismatch, incorrect native transform or nonmatching centered replay. Expected
coverage losses remain results, not reasons to silently move transects.
Fresh archive `local_archive/experiments/S03-E016-D01/runs/S03-E016-D01-R001/`.
Receipt, scored tables/arrays, all-beam figures, README_analysis, blind packet
and a separate pending independent-reference status required. No claim closure
until independent reference and reviews exist.

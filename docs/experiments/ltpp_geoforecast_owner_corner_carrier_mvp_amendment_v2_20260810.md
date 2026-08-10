# LTPP owner-corner carrier MVP v2 amendment — 2026-08-10

## Reason and timing

The v1 owner-corner packet was initialized but remained empty: all eight dates
had zero saved points and zero locked records. Before any corner collection,
the owner asked the agent to continue actively. The empty v1 packet is retained
and is not overwritten.

## Single protocol amendment

The v2 interface may display one four-corner **agent-proposed visual
suggestion** per date. Suggestions were obtained in a read-only examination of
the frozen `segment_0_50_white.png` images, using only the centreline
intersections of the printed outer solid boundary. Crack shape, WIM, repairs,
distress marks and cross-date crack correspondence remain prohibited.

Suggestions are visually distinct, do not populate `points_source_px`, and do
not count toward completion. The owner must explicitly adopt a suggestion or
click four points manually, inspect the labelled polygon, and lock each date.
Adoption remains an owner-visible construction-control decision, not an
independent or blind annotation.

The proposed source-pixel points, in fixed `TL, TR, BR, BL` order, are:

| Date | TL | TR | BR | BL |
|---|---:|---:|---:|---:|
| 19910610 | (218, 242) | (2582, 176) | (2589, 778) | (218, 844) |
| 19951024 | (526, 175) | (2572, 171) | (2570, 830) | (524, 831) |
| 19970228 | (599, 251) | (2642, 251) | (2637, 897) | (519, 897) |
| 19980407 | (588, 259) | (2627, 258) | (2622, 903) | (582, 903) |
| 20010913 | (585, 242) | (2631, 242) | (2631, 942) | (585, 942) |
| 20030514 | (570, 138) | (2601, 138) | (2601, 866) | (570, 866) |
| 20071106 | (572, 106) | (2601, 109) | (2598, 796) | (567, 796) |
| 20120417 | (560, 196) | (2770, 185) | (2769, 903) | (560, 911) |

These are review accelerators, not validated controls. If adopted, their
provenance remains `agent_proposed_owner_visible_construction_candidate`.

## Unchanged boundaries

All v1 input hashes, fixed point order, physical 50 ft × 15 ft rectangle,
one-way date locking, visual-overlay review, statuses and prohibited claims
remain unchanged. This amendment does not run a transform, calculate physical
registration errors, inspect final controls, or run a final gate.

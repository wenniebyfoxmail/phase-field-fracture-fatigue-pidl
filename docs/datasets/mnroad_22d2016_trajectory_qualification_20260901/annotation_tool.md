# MnROAD 22-D-2016 single-owner crack annotator

This local browser tool implements the qualification protocol in `report.md`.
It is limited to manual centreline vectorisation and chronological identity
linking; it does not recognise cracks automatically and does not promote the
dataset to model-ready status.

## Create the frozen packet

```bash
python3 scripts/mnroad_single_owner_crack_annotator_server.py prepare \
  --download-work local_archive/real_road_acquisition/mnroad_22d2016_source \
  --packet local_archive/real_road_acquisition/mnroad_22d2016_annotation_packet
```

The command verifies all seven official PDF SHA-256 hashes, renders ten pages
per date, creates 70 primary page tasks, and inserts 14 concealed repeats. It
refuses to overwrite an existing packet.

## Annotate

```bash
python3 scripts/mnroad_single_owner_crack_annotator_server.py serve \
  --packet local_archive/real_road_acquisition/mnroad_22d2016_annotation_packet
```

Open `http://127.0.0.1:8776`. In phase 1, click along the visible crack
centreline and press Enter to finish a `LineString`. Complete the properties,
save, then lock each task. Excel totals, repeat identity, other map dates, and
crack identity are not exposed by the phase-1 UI.

For a reviewed page with no Driving-lane NWP, leave the geometry empty and
click `确认本页无目标裂缝（0）` before saving and locking. An unconfirmed empty
page cannot be locked. A visible but ambiguous mark is not a zero: draw it and
set the class to `unresolvable`.

After all 84 phase-1 tasks are locked, open `http://127.0.0.1:8776/link`.
All tasks are then presented chronologically (the repeat key remains hidden).
Geometry is frozen;
assign persistent `crack_id` values and one of `persistent`, `extension`,
`nucleation`, `not_observed`, or `unresolvable`. No transition may cross the
2019-10-24 crack-sealing event.

Keyboard shortcuts: `N` new line, `Enter` finish line, `Z` undo point, `S`
save, and left/right arrows change tasks.

## Export

```bash
python3 scripts/mnroad_single_owner_crack_annotator_server.py export \
  --packet local_archive/real_road_acquisition/mnroad_22d2016_annotation_packet \
  --output local_archive/real_road_acquisition/mnroad_22d2016_annotation_export
```

The export contains primary-only GeoJSON, a repeat-inclusive audit GeoJSON,
and a QC summary. The QC summary calculates repeat total-length agreement,
crack-ID length agreement, and median symmetric vector distance. The default
pixel scale is the diagnostic 21.4 px/ft and must be independently checked
before using length results. Lane-leakage review and Excel reconciliation
remain promotion gates rather than automatic claims.

# Moving IB ruler data characteristics

2026-10-11; all three preregistered development references inspected.
R001 retrieved 3/3 released-v4 PNGs: uncompressed sizes, manifest CRCs and
decoding passed. All images are 3024 x 4032 portrait. Beam 6 ref2 remains
unretrieved and unviewed by this work.

## Observed capabilities

- All three show the beam identity, a long ruler section, mm tick bands and
  legible centimetre numbers. Named physical marks can be selected independently
  of the automatic peak sequence.
- The ruler is approximately horizontal but changes slope and vertical position.
  Beam 4 is clearly tilted; Beam 5 and Beam 6 are closer to horizontal.
- Beam 4 and Beam 6 show a rounded ruler end; Beam 5 shows a rectangular end.
  Tick numbering/direction differs. A ruler origin or period cannot be copied
  from another photograph.
- The metric carrier is near the lower part of the beam, while a large part
  of the portrait frame is apparatus/background. A crop fraction remains
  a camera-specific assumption. Photographs contain contrast variations,
  scratches and non-ruler structure that can create misleading line/peak fits.
- The numbered marks are promising reference evidence; their exact pixel
  locations and annotation repeatability have not yet been measured.

## Method decision

Use known cm-mark identities to anchor a 1-D coordinate. Start with a linear
map from a few named marks, compare a projective map only if held-out named
marks show that perspective matters. Assign mm labels from printed numbers,
not from an estimated periodic peak count. Check a second annotation pass.
Report only along the ruler's direction within the marked span.

The six fixed and three moving references are development evidence. One
reserved moving Beam 6 ref2 can test one fresh observation, not a safety-rate
or unseen-beam generalisation claim. Reference annotation and attainable error
must be resolved before freezing a formal threshold.

## Computation can proceed in canonical pixels

S03-E006 already established local IB registration for three beams, two stops,
one fixed and three moving observations per stop. Its 27-file archive contains
the reference planes plus 24 state photographs. It supports a C0 local
observation-token pipeline using canonical pixel coordinates and exact
beam/stop/view lineage. A mm calibration is only needed for mm outputs.

Next MVP: serialize simple patch observations and registered view metadata,
then compute descriptive within-stop cross-view differences. Use all archived
IB state views; retain zero-coverage/missing patches explicitly.
No crack mask or independently measured width is present, so these tokens
represent image observables. Their differences are not proof of crack growth.
The load-stop identity is categorical acquisition metadata; fixed/moving
photographs are not exactly synchronized and must not form an invented
continuous image-force trajectory.

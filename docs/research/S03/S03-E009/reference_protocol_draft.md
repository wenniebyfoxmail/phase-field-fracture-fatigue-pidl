# Selective directional scale measurement — draft

Status: reference design only; not a frozen accuracy experiment.

1. Display ruler pixels without detector outputs. In each development image,
   mark at least six legible numbered cm positions across a contiguous span.
   Record file, ruler band, physical label, native x/y, observer/pass and
   ambiguity. Follow each printed number to its long tick; do not mark text
   centres or assume every strong peak is 1 mm.
2. Repeat the marking without seeing the first coordinates. Quantify
   annotation disagreement; uncertain mark identity goes to review.
   Separate-process marking is not an independent gauge of crack width.
3. Fit a linear directional coordinate using a fixed subset of named marks;
   score omitted named marks. Compare a projective map on the same marks,
   using repeatability to decide whether added flexibility is warranted.
4. Evaluate an automatic detector against these externally assigned ruler
   labels. Internal LOMO and peak counts remain diagnostics.
5. Freeze image-level acceptance using observable image quality and detector
   QC before the reserved image is viewed. Scoring-reference labels must not
   tune the policy. Report accepted count and all errors, including abstentions.
   Require non-empty coverage: a reject-all system cannot pass.
6. Calibrate the error tolerance from reference repeatability and the intended
   directional-mm decision. A 1 mm engineering tolerance is only a candidate
   until reference noise is known. With one reserved image, any zero-error
   result is descriptive, not evidence of a near-zero population risk.

Inputs now possessed: six fixed and three moving development references.
Reserved: moving Beam 6 ref2. Formal-code/evidence review is still pending;
this draft authorizes no formal accuracy claim.

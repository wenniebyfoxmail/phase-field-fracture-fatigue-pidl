# E016 actual training-side spatial assets — 2026-10-15

## Scope and provenance

S03-E016-R001, local preparation only, explicitly authorized by user.
Worktree codex/s03-e016-geometry-alignment-20261013; source declared clean
bc7c21645e797607b73dcc374421e29808ba5884, numerical bytes reviewed at35fd968.
Mac hostname Wennies-MacBook-Pro-14.local, PID97501, Python3.12 / NumPy2.2.6.
Started2026-10-15T12:29:35.164344Z, completed12:29:37.630140Z (2.466seconds).
No remote execution or solve. Exactly3 future solves unchanged, not launched.

Local root:
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016/S03-E016-R001
See00_intent.md, prepare/execution_receipt.json and figures_v2/render_receipt.json.
Original ZIP size/MD5 matched the prospective protocol. Only13/14 nodemaps
converted. Stage15 scalar headers and whole-member byte identity bound as
per protocol; response arrays/coordinates/strains NOT converted or interpreted.
No stage15 validation, fit package, held scores or physical inversion exists.

## First preparation findings

- cycle292018.5/reference1; loads4498.182774/9746.675491/15001.544952N,
  alpha2.0012149665931886 (header-derived, not response-derived).
-39970 jointly finite XYZ/UVW training nodes; maximum reference mismatch
  [4.00e-9,3.00e-9,3.00e-8]mm. All spatial operators use stage13 coordinates.
-861nodes,1600CSTs,120BCnodes,648common strictROI observations. Source lumped
  weights positive, min0.10314744/max0.69209757mm2, sum426.02280563mm2.
- All53paired queries supported for each of3.6/1.8/2.7mm gauges; main106queries
  and120BC queries meet rank3 and fourth-distance<=2mm.

| Gauge b [mm] | Halfheight left,right [mm] | Peak [mm] | Halfheight lobes |
| --- | --- | --- | --- |
|3.6 PRIMARY| -8.28670869,6.92142423 |0.00897606921|1|
|1.8 descriptive|0.84738523,1.37886926|0.14896102957|1|
|2.7 descriptive|-1.31693709,7.07178791|0.00907016368|2|

Primary old→new center -1.5→-0.68264223mm (+0.81735777); length
15→15.20813292mm (+0.20813292); left/right changes +0.71329131/+0.92142423mm.
This is joint prior position/length adaptation, not measured crack-tip movement.

| Quantity | Old | Proxy |
| --- | --- | --- |
|Discrete prior integral [mm2]|60.30087920|60.90935813|
|Area-mean local multiplier|0.85517814|0.85371397|
|Intact-normalized area-mean local degradation fraction|0.14482272|0.14628688|

These are artificial-mesh prior/local-multiplier summaries, NOT real crack
area, patch effective stiffness or independently identified physical damage.

## Conditioning and model-assumption warnings

| Operator | Maximum condition number | Maximum coefficient L1 | Maximum fourth distance [mm] | Queries with negative coefficients |
| --- | --- | --- | --- | --- |
|main3.6|3.77429433|1.44405372|0.97550117|25/106|
|aux1.8|1464.37861386|646.90617357|1.77842145|32/106|
|aux2.7|4.65992217|1.84401411|1.26937606|30/106|
|BC|5.40053568|2.02238637|1.31148360|43/120|

Aux1.8 upperquery(0,1.8) coefficients approximately
[263.16845,-221.00407,-101.94902,60.78463], ID[20971,21183,20758,21396].
This is strongly amplified affine extrapolation, not convex averaging. Its
large negative valley and neighbouring positive peak must not be interpreted
as a physical opening/tip measurement. Aux2.7 has two separate halfheight lobes.
Different auxiliary intervals show gauge/local-operator sensitivity; no auxiliary
band replaces the frozen mainband, no deletion/filter/new threshold is introduced.

OLS-plane tilt0.01883776degrees, orthogonal RMS0.01716718mm, maximum0.23431605mm.
Raw DeltaUVW RMS[0.00222352,0.00403363,0.00632913]mm: W is not negligible
relative to in-plane increments. These are descriptive limits of the2D/static
approximation, not authenticated export compensation, stress-state validation,
or an automatically imposed failure/rotation rule.

## Visual QA and independent admission

Initial full-field spatial panels made the patch too small. A renderer-only
change atfbb4a772ae9bd97ca2ca0892e4087759b63bc9fe preserves the full-field
overview and uses readable common local bounds for prior/BC panels. Numeric
runner/dependencies/fourPREP files unchanged. Old figures retained; figures_v2
is the proposed current set.22synthetic tests passed after renderer-only change.
Main agent opened both actualPNG figures: full curves, auxiliary anomaly and
two-lobe shape retained; local priors/BC readable, full support overview kept.
No smoothing/clipping of profile values or selected examples. PNG/PDF, README,
same-stem sidecars and source-bound render receipt retained locally.

## Independent read-only Codex admission — PASS_ASSETS

Reviewer /root/e016_code_review independently admitted the actual numerical
training assets for the declared three-static-solve PROCEDURE comparison,
using figures_v2. No remaining required admission repair found. This is NOT
physical crack-tip truth,2D-model validation or execution authorization.

Reviewer verified PREP complete/source/current runner/four-dependency/four-artifact
bindings, render source/plotter/all-artifact bindings, originalZIP size/MD5;
opened ONLY stage13/14nodemaps and connections13. Stage15member was NOT opened.
Independent recomputation matched joint39970 support,648scorepoints, positive
weights/426.0228056mm2 sum,861/1600/120mesh and648mm2 artificialmesh area,
all neighbourIDs/order/sides, coefficients/amplification,14tailtrend, main/aux
halfheight, coordinate mismatch, BC, priorintegrals andOLS plane residuals.
Maximum maincurve recomputation difference about7e-18mm; all120BCs consistent.

Specific independent warning attribution:

- aux1.8 upperx0 raw source DeltaV values roughly-0.0010..0.0037mm combine under
  very large affine coefficients into the huge anomaly. Lowerx0.9 is also
  ill-conditioned. The0.53148mm auxiliaryhalfheight length is not reliable physical
  crack length; neither its spike nor large negativevalley is a trueopening claim.
- aux2.7 valley nearx=-1.8 is propagated from sourceID21814 DeltaV=+0.015259mm
  versus nearby-0.0071..-0.0076mm with positiveweight0.3325. Local upper/lower
  conditions about3.66/3.17 are not comparable to theaux1.8 pathology. The source
  inconsistency is confirmed; physicalversusDIC/export origin remains unknown.
- Small plane tilt does not establish2D adequacy; raw W RMS remains material.

Reviewer opened both actualv2PNG files, confirmed readablelocalprior/BC/fullfield
overview and complete unsmoothedprofiles/anomalies. PDF identity checked but not
separately page-rendered. No prepare/fit/validate/FEM invocation, edits, network,
outbound files or additional agent contacts by reviewer.

Decision: keep the frozen mainband and prospective exactly3solve comparison;
carry conditioning/gauge/source/2D limitations. Primary held contrast remains
uncomputed and physical recovery unestablished. No fit/validate launched; user
explicitly requires a stop before solving and stage15 response conversion.

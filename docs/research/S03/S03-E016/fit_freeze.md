# S03-E016-R002 — source-bound prediction freeze

2026-10-15. User authorized the exactv1packet to drtao/GPUServer8, one three-arm
q=0staticfit, monitoring and retrieval, explicitly excludingstage15response access.
Execution succeeded / retrieval verified. Scientific primary contrast pending;
this does not close E016 or establish physical damage/material/future validity.

## Provenance and command

Source snapshotd0c2bbee1ccf0072e7e776bde6fdf8faa788a0fc, numericalbytes identical
to independentlyreviewed35fd968. R001preparedassets independentlyadmitted.
Approvedtransfer2445698bytes, SHA2567d1bb9248788260eefcf3c77e55ce497d02b03ce2c4abd5db535e60a4ddda9e6;
11regularfiles verifiedremotely, noZIP/heldresponse/filelinks/extra source.
One scp transfer was slow but continued; no resend or alternateproducer used.

Producer gpu-taobo / GPUServer8, sharedaccountdrtao.
Root /mnt/data2/drtao/wennie/S03-E016-R002; PID1744429.
Log logs/fit.log(empty); launch.json andtransfer_verification.json recordPID,
source/runtime/threadpools. Python3.10.12/NumPy1.24.4/SciPy1.15.3;
NumPy/SciPyOpenBLAS each1thread, CUDA_VISIBLE_DEVICES empty/noGPU.

Command under approved single-thread/cache environment:

```text
/usr/bin/python3 -u code/scripts/aa2024_geometry_prior.py fit
--input /mnt/data2/drtao/wennie/S03-E016-R002/prepare
--output /mnt/data2/drtao/wennie/S03-E016-R002/fit
--source-commit d0c2bbee1ccf0072e7e776bde6fdf8faa788a0fc
--run-id S03-E016-R002
```

Start2026-10-15T15:00:11.736905Z, end15:00:12.086666Z;
elapsed0.3497632723301649seconds<600softwholefitbudget. Old/proxy/intact each
solvedonce; qR=qL0, no search or retry; secant computedwithoutsolve.
All three complete fields and fourpredictions frozen beforeresponseaccess.

## Numerical completion, not held performance

| Arm | Relative static residual | Training vector MAE [mm] |
| --- | --- | --- |
|old|1.6030626449971995e-15|0.001012759005745383|
|proxy|1.5453649182819247e-15|0.0009973905951758109|
|intact|1.4437545005900372e-15|0.0014978337759763022|

All residuals below1e-8, field/sample/prediction arraysfinite. Training MAEs are
descriptive only; do not use their ordering as high-loadvalidation or tunepriors.
Maininterval[-8.286708688,6.921424233]mm, fixed36x18mesh,861nodes/1600CSTs,
120BCs,648observations/positiveweights, alpha2.0012149665931886 unchanged.
Aux1.8conditioning/aux2.7sourceinconsistency/non-negligibleW limits retained.

## Retrieval and arithmetic verification

Localroot:
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016/S03-E016-R002
Resultbundle144261bytes SHA256e137866d91c0078e2b2f50ba3eb8ec40eb110b7e91ccdb767dc1205613563d0d.
Eightfile whitelist verifiedbeforeextraction; allrequiredfit/log/environment/PID
outputs present. Fitreceipt SHA2563173f0f659d6e451f7fccc39a4ca0973ae3caad750c9d98ce754a1bcec325674.

Remote andlocalchecks confirmed currentrunner/fourdependencies/threefitartifact
hashes, fit-to-originalR001 bindings, allfrozen ids/coordinates/weights/u13/alpha,
prescribedboundary values, priors/intactzero, sampling and fouralphapredictions.
No localFEMsolve or heldparser invoked. See02_download_verification.md locally.

MacNumPy2.2.6 rigidprojection matmul warneddivide/overflow/invalid despite finite
matching results; remoteNumPy1.24.4 logempty. Independent scalar closedform
weightedcentroidtranslation/rotation (no matmul/lstsq/solve) matched recorded
trainingMAEs at maxdifference2.168404344971009e-19mm. This is a producer-side
arithmeticcheck, not a new independent evidence review; no rerun or sourcefix.

## Stop point

Stage15response not transferred, read, converted or scored. Frozenoutput delivery
is complete; no primary old-minus-proxy heldcontrast, four-arm heldfigures or
physical inversion claim yet. No further outgoingmessage/file action authorized.
Next separate step: finish/review held-result rendering and seek explicit
stage15validation approval; retain the current predictions without furtherfit.

# C1 r4: raw operator consistency and displacement-response admission

Prepared 2026-10-16, synthetic development C1 numerical/state-transition
comparison, supplementary to frozen E011. Prospective amendment to
[c1 sequence protocol](c1_commit_protocol_20261015.md), not a reclassification
of [v3](runs/c1_commit_v3_result_20261016.md). No v4 transfer or native solve.

## Question and admissible comparison

Can the original/repaired one-c1 sequence be compared after separating two
questions: does each raw field implement the declared Q4/Amor operator on its
own displacement, and is the difference between two outputs accounted for by
the actual allowed input difference? Original u/d/history/count gates remain
mandatory. The prior cross-state raw clause conflated these questions.

Unit: independently propagated original/repaired five-substep c1 from one
original recovered initial state/KK. Horizon one loading/unloading cycle.
Same8inputs: state0+metadata+native mesh+five oldpostcommit states,156839354bytes.
All are exposed development evidence; no new holdout or physical independence.
Same86756nodes/86408Q4/GP4, E1/nu.3/plane strain, existing material/loading,
original numerical loops, coupled repair and budgets. No native runtime change.

v3 remains failed: its raw pointwise screen5.0122e-10>1e-10. No threshold is
changed in v3. r4 changes the reference-admission estimand prospectively; a new
pass will NOT mean the old raw pointwise gate passed. Store both labels.

## Analytic response budget, fixed before new execution

Engineering strain e=[exx,eyy,gamma_xy], t=[1,1,0], mu=1/2.6, K=1/1.2:

psi(e)=0.5 e^T D e+0.5 K max(t^T e,0)^2,
D=2mu[[2/3,-1/3,0],[-1/3,2/3,0],[0,0,1/2]].

Its gradient is D e+K max(t^T e,0)t. Positive-part squared is C1; its gradient
is globally Lipschitz with safe L=||D||_2+K*||t||_2^2=2mu+2K=2.435897435897436.
This bound holds across positive/negative trace changes, not just fixed branches.
The fundamental theorem of calculus and the Lipschitz gradient give

|psi(e_c)-psi(e_r)| <= ||grad psi(e_r)||2 s +0.5 L s^2 = B_response,
s=||B_Q4 (u_c-u_r)||2.

Use actual nodal delta-u and apply B directly; do not subtract nearly equal
strains for s. Report the difference between these two strain computations as
a roundoff diagnostic, not an adjustable epsilon. The bound uses no fitted
factor, data-selected floor or changed material coefficient. This is a
floating-point implementation of an exact-arithmetic bound, not an IEEE
certification. Unexplained violation stops; do not add numerical slack on sight.

Fixed tau=1e-10, retained from the old raw operator-precision level. At every GP
compute independent own-field replays pc=psi(Bu_c), pr=psi(Bu_r). Require:

1. |raw_c-pc| <= tau max(1,|pc|).
2. |raw_r-pr| <= tau max(1,|pr|).
3. |raw_c-raw_r| <= B_response + tau max(1,|pc|)+tau max(1,|pr|).

The two absolute consistency budgets follow from the two preceding checks and
the triangle inequality. Clause3 is a budget-consistency check, NOT independent
solver-equivalence evidence. No argument that an arbitrary raw gap is acceptable
merely because one can fit an amplitude or choose a larger fixed threshold.
Zero unloading retains absolute budgets; undefined relativeL2 remains null.

## Exact original-admission change

Keep u/d max absolute error<=1e-10, actual proposedhistory2:4 scaledmax<=1e-10,
exact outer-count match, source/MEX/geometry/state identity unchanged. Replace
only the old cross-state raw equality clause with the three checks above.
Retain raw_scaled_maxerr and legacy_raw_pass in every reference record/CSV;
mark raw_admission=q4_amor_response_r4 in manifest, commonmetadata and terminal
result. A raw pass cannot rescue any failed u/d/history/count clause.

Original arm must pass ALL5 new-admission reference screens before repaired
arm starts. Existing original native cached acceptance remains observationally
separate from freshC. Repaired primary is unchanged: finite/bounds/fixedBC,
PRE-COMMIT oldlower/history C=max((Ru+Rdfeasible)/4e-6,Ru/1e-8)<=1, then exactly
one native history proposal/newlower=d and durableaccepted version per step.
No postcommit rescue, extrareset, retry, nextstep after miss or budget increase.
20blocks/250u+250d inclusive per repairedstep; original existing caps unchanged.

## Independent implementation and pre-solve admission

New pure MATLAB e011_raw_equivalence independently reconstructs analytic
Q4basis/Jacobians/gradients from immutable node/connectivity, explicit native
2x2GP order (.577350269189626 signs), engineering shear and E1/nu.3.
It checks actual native GP/Nxi/dNdxi/weights against this declared geometry;
asserts positiveJacobians and finite inputs. Original reference call also checks
material/E/nu/eta/materialid/plane-strain contract. No assembly callback,
stiffness getter/cache, tangent mutation or accepted-state assignment.
No global/persistent geometry cache; no cache-identity ambiguity.

New16file package:14MATLAB including entry, JSONmanifest and PSlauncher; one
newhelper incorporates12 tiny algebra tests. Entry still strictNASGU/MSNU only,
source/which/MEX, old22tests plus12rawtests=34pendingactualWindows tests.
Actual worker also applies independent own-u rawcheck to ALL5 oldreferences
during8inputreadpreflight, before System initialization/nativefields. Save five
small summaries in io_preflight.json. These are read-only replays,0nativecalls.

## Existing evidence and tests

At observed v3s3 worst olderror GP: gap1.30600819e-9, actual-input analytic
bound1.49735090e-9, two own-u budgets add5.21131869e-10; total2.01848277e-9.
Maximum gap/budget .6470246906; ownerrors9.1931e-13/1.2720e-12. These records
support feasibility of this different admission definition only. Allfiveold
references' ownfieldchecks pass; s4/s5 NEWcandidate behavior remains unknown.

Offline independent explicitJacobian implementation agrees with existing
q4_geometry/Amor replay. Six rawfield negative controls reject stale raw,
common offset, wrong GP, material coefficient, half engineering shear and
transposed gradient rows. Four additional nonraw clause logic checks do not
count as producer injection tests.20000seed1 random strain pairs across scales,
including722tracecrossings, satisfy the response budget; mathematical argument
above, not Monte Carlo, establishes the exact-arithmetic bound.
MATLAB's12tests cover affine, rigid, both tracecrossings, engineering shear,
wrong GP/commonoffset/staleraw/material/half-shear/geometry, zero unload.
They are NOT_RUN until the approved Windowsentry executes. No new local solve.

## Outcome, evidence and approval

New run proposed pf_s04e011_c1_commit_20261016_v4, CITPC12/AD\xw436,
C:\Users\xw436\jobs\E011_C1_20261016_v4. Freshroot,16filehashes,8ordinary
inputcopies/fullhash, >=10GBdisk/6GiBRAM/noMATLAB, detachedWMI/CPU1threadR2025b.
Exact final package/account/command/copies and version-specific local-review
substitution require user approval. No send, copy, native launch or push yet.

Any failed admission/field/primary stops without restart or nextstep. Retrieve
allstate/proof/rawresponse/transaction arrays, log/receipt and input identities.
New analyzer branches ONLY on r4manifest and independently reproduces the new
checks; oldschema still enforces old rawgate. Retain both old/new labels in
CSV/JSON and explain admission revision in figures/README. Minimum output:
all5old/newreference errors, pairedprecommitC and commit versions, GPweighted
active/history differences, missingsteps explicit, figures+sidecars, independent
review and updated mesh对齐.md. Scopeone syntheticc1; no120cycle/Nf/c83/teacher
or physicalclaim. If future rawselfcheck fails, locate operator/state/GP first;
if nonraw divergence fails, investigate original reproducibility; if repairedC
fails, identify first coupled block/substep, preserve original verdict.

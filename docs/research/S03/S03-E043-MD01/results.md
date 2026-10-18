# E043 results — 2026-10-18

Exploratory frozen-mask repair, one development-exposed trajectory. User revoked
the old80%usage stop rule and explicitly retained identification/oldhalfdepth/scores.

Newdefinition L=occupiedimagerows, M=meanpositive rowcandidatecount, A=L*M exactly.
Predict L bypersistence and M bystage-adjusted secant; no fit/parameter selection.
M is conditionaltotalrowmass including shadows/branches, NOT crack aperture,
normal-width, EDT oroldhalfdepth. L is nottruecracklength/recall. Sameband250×700.

Allfixedwindows persistence/areasecant/separatedAE(px²):
18,19→21=2311/2953/2268.8011;
19,21→22=511/644.5/73.1192;
21,22→23=492/19/19 (floatingtie; priorE037query).
EqualwindowMAE1104.6667/1205.5/786.9734; separated reduction28.759%vs persistence,
34.718%vs areasecant. Calculable3/3, notindependentreplication. Latefixedsupport
necessarilyreduces toareasecant; noextra independent latevalidation.

Componentgain: support/mass separation preventsmixing detectionspan changes into
wholearea slope. Earlycase remains poor, predictedL151 vsobserved250, mass11.823
vs16.216; error2268.80(~56%target). Supportpersistence doesnotpredict revelation.
Unknownshadow/texturefalsepositives remain inboth L/M; noactualmaskaccuracygain
orphysicalgrowthclaim. No truthlabels orartificialcomponent attribution.

Allninecachedsettings, samefixedrule:7/9beatpersistence,8/9beatareasecant; no best
settingselected. contrast_minus5loses topersistence;guide_x_minus5loses toboth.
Somearms duplicate, not9 independentexperiments. No clipping among27predictions.

Cleanproducer999eeeeb1dfedb07baaacb9412f6a5b3286099f2, R001 succeeds0.232s;
148inputhashes unchanged, oldE042all15filesprotected, 36originalprotectedfiles
unchanged. E041acceptedStep19commonmask=v1exact. OldE042nominalbaselinesexact.
Syntheticfactorisation/missingness/gaps/capstests and27rational-arithmetic
postchecks passed; localchecks, no independentagent/modelreview.
R002visuals bothPNGactuallyviewed,4files/2sidecarspassvalidator. Raw/maskpanel
reusedunchangedfromE042, no fresh image access. Source/evidence:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E043-MD01/runs/S03-E043-MD01-R001/README_analysis.md`.

Next: retainfixedrule andtest a separatelyfixed additionalstage/window tocheck
developmentgain without errorselectedparameters; shadowrisk remainsexplicit.
No additionalimageopening/evaluationexecuted here. No D01 duplication.

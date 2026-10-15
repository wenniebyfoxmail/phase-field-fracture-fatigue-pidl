# Independent review — E024, 2026-10-15

Reviewer `/root/halfdepth_code_review`, read-only; no matching, pixels, fitting,
training, aggregate runner or external messages/files. Source review before
execution, independent numerical recomputation and actual final image QA.

## Code and design

Confirmed E019 local_grid/match_patch and sampling convention: shift_t already
origin-native t=(-ny,nx) pixels; subtract same-stage FITmedian for aligned arm.
No norm/resize conversion. Fixed CHECKa4..7/T1a5 exclusion, full predefined
eligible support or unassessable,36opportunities per arm and141/144 nominal
CHECK pairs retained. Matched-ID M primary, Cartesian cross-ID secondary;
parallel flags plus fixed mutually exclusive priority; A<=2 absolute limit,
strict .5ceil and finite-grid-only interpretation. e0=0 reference not truth.

Initial review requested stronger source validity replay: eligible81pair cells,
band valid==grid, strict amplitude flag versus max deviation, and stage0
available ANDzero. Main added checks/refusal regressions before execution.
Clean6deebc0bf0080c142abdb7feb8c822699d878aec verified;23tests independently
passed0.086s, renderer static mapping reviewed, no R001 execution blocker.

## Independent actual recomputation

Without E024assess/calculate, used E019 anchors/translations and E023 bands to
recompute384stage residuals,288CHECK pairs,72classifications, all primary and
secondary summary fields. All match within1e-12 arithmetic comparison, not
metrology precision. Input7paths/bytes and upstreamclean identities verified;
numericclean6deeb, wall.020975166s/CPU.012875s, threads1, success.

Original states21compatible/10beyond/4common-sensitive/1outside; aligned22/8/6/0.
Amplitude-qualified compatible17/20;141/144perarm, no new missing, T1fixed3.
Originalall3[4,6,9,10], alignedall3[4,5,6,9,10,12]. Both-arm amplitudeall3
[4,6,9,10]; cross secondary loses originalT9/T11/40→50 and alignedT8/30→40.
OriginalT12/40→50: A2.0216699256765636, M.3987147730494498; outside support,
not measured physical crack-edge error or automatic reversal.

## Plot-only repair and actual final QA

R001 initial figure1 arm title/transition labels and longylabels overlapped;
figure3ylabel crossed panels; figure4annotation covered extreme green points.
Both main and reviewer detected. Renderer-only b3a064bac700afa3051b118591c420d4b5f03bff
diff13lines reviewed: no data/statistic/classification/axis change, labels moved
or shortened. R002 wrapper import-path failure before output is technical,
not a numerical failure. Fresh R003 addsPYTHONPATH=scripts and succeeds.

Reviewer actually viewed all4R003PNGs: labels clear; same36sort/12x3map/
24signed trace panels; both extreme scatter points visible; shared axes intact.
Figure2 independently cmp byte-identical toR001. Raw/state definitions and
matched-versus-cross nested warning correct; no physical usability upgrade.
Cross-run guide-source pointers repaired, all resolve to R001; no numerical
or image changes required.

## Final wording check complete

README all12position table/counts, compact summary, Outcome, R001/R002/R003
identity records, S03 and Obsidian checked. Original21/aligned22 and amplitude
17/20 correct; originalall3four/alignedsix, both-arm amplitudefour and cross
secondarythree are correctly distinguished. T7 .1325898881/last-safe0 and T12
A2.02167/M.398715 not called physical failure. T4/6/10 development priority
does not replace primary or old scores; T9spatial-transfer caveat retained.
No new fractional sampling/repair/forecast claimed. R001numeric6deeb,
R002wrapper import failure, R003renderb3a identities separate. Five Markdown
guides/README links resolve, renderer3line change is future guide paths only.
Final user-facing scope remains conditional tangential optical-development
proxy evidence, not physical usability or actual material correspondence.

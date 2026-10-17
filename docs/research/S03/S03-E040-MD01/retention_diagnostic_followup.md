# Post-gate retention explanation, read-only extension

2026-10-17. R008's post-hoc accounting finds1974releasedleftcrop pixels pass
allfixedpixelgates yet are absentfromsavedE040mask; their nearestguidedistance
min27px, so none locally contacts the12px seed zone. This does not identify
wholecomponent admission because connections outsidecrop matter.

To finish diagnosis without a newcandidate: group cachedR008pixel_gate_eligible
by8-connectivity overtheoriginalROI, read each component's existing height and
whetheritcontacts guide<=12px. Check consistency againstactualsavedmask counts,
do not construct/write a newly selectedmask, alter thresholds/support, re-read
newsource orrunextractor/metrology/prediction. This is an explicitly post-hoc
arithmetic explanation ofexistingretention, not formal confirmation or a new
segmentation. Initial R008 no-component phase remains immutable and its own
constraints satisfied; this separatelyrecorded explanationR011 introduces only
component labelling ofcache, not component reselection or change tooldresults.

CapCPU/wall30s. PreserveR008arrays/summary, E040R001arrays/summary/receipts and
alloriginalprotectedinputs byhash. Report localreleasedpixel counts by failed
retention condition andcompleteinvolvedcomponent ledger. Components/pixels include
pores andtexture; no crackrecall/precision, humanlabels orcausalpercentages.
No newmask orproducer prediction authorised byHQcoordination. Only remaining
repair may be specified as source-basedguidealignment candidate, not evaluated.

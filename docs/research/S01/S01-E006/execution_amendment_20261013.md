# S01-E006 execution-only cache adoption amendment

Original reviewed runtime `5d973b3`, source manifest
8221ff3b5dc9ed53dcaa5036910644e3fbc27607c9e34d6cd6d93beaa7d59583,
completed extraction, four fixed regression heads and all train/validation
features in S01-E006-R001. At19:51:57+01 it stopped before selector fit:
recorded held-location lists were serialized lexically while the verifier
expected numeric order. The memberships, training exclusion and heads were
correct; no selector fit marker, model or detection evaluation was created.

Normalize held-location metadata numerically when checking membership, require
four unique held locations, and preserve all regression identities/parameters.
After independent new exact-source review, fresh S01-E006-R002 may **adopt** only
this exact manifest's completed extraction cache. It must first replay all source
hashes, original classifier scores, fold training membership/scaler/objective/
gradient and held predictions, paired banks/labels and features. Reject a source
with any selector fit/evaluation/authorization marker. Copy arrays unchanged;
rebind only metadata source lineage and record parent/new hashes. Verify again
before the one unused selector fit. No new CNN extraction or regression fit.

This repairs execution, not the model, labels, primary criterion, score, data
split or budget. The scientific budget remains4 actual fixed regression fits,
1 selector fit and1 development comparison. Original R001 is preserved failed/
retrieval-qualified with uncomputed scientific verdict; R002 records adoption.
PowerShell now captures complete native stderr while checking native exit status,
so an error cannot collapse to only the first traceback line. New review is
required before any adoption/fitting. Fresh locations remain sealed.

# Exact-commit Code Ready review round 1

- Reviewed commit: `3e17a04`
- Reviewer: ChatGPT Pro through the authorised Haofan account
- Conversation: https://chatgpt.com/c/6acc15e8-27b8-8331-aa38-ad6b8aeacfc8
- Verdict: `MODIFY_AND_REREVIEW`
- Scientific U0.125 arrays decoded at review time: no

The review identified eleven blockers. The first submission omitted the data
lock, source metadata evidence, and imported E004 dependencies from the review
package. The builder also decoded earlier states before verifying the complete
73-file inventory, did not bind the static/source identities before reading,
could under-report a failed first scientific read, rounded qualification
metadata, and accepted output suffixes that NumPy could silently alter. The
runner allowed fixture mode in production and audit mode on an arbitrary
packet, made packet identity optional, ran producer guards after packet/model
work, lacked an experiment-wide single-attempt marker and durable per-cycle
progress, mishandled undefined denominators, and omitted deterministic
worst-cycle identities.

Required disposition: repair all blockers, add targeted fixtures, freeze the
analysis path before unsealing, commit the changes, and obtain a new review on
the exact replacement commit. This review does not authorise packet building or
Taobo inference.

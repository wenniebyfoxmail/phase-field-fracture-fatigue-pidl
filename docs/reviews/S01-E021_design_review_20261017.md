# S01-E021 independent design review

Reviewer: existing e008_independent_review, **gpt-6.1-sol / Medium**. DESIGN PASS; no blockers. Exact commit d3eb8937ee52a37f47d17c64b22bffee30e0001a. Config e80885b7f9052994c335215938959749cc7fe0fabe49beeae8396e08f50bc087; lock ab8bfff4a4594717ae66ba968b8db0b81742a652d37237a2323431aecb3a2b80.

New information is pixel-to-original/corrected-box spatial correspondence, not another pooled-cache compressor. Shared context,centre masks,four-direction response,area baseline,C/D and degeneracy are specified. Shadows/textures/scale/light-crack risks do not mistake the response for GT. Held fixed feature computation fits nothing; own-FIT heads/gate remain isolated.39solves,188214predicted row vectors and835+at most6=841reads/decodes agree;3/5/6 actual gainGT limitation remains.

Implementation must hash/decode same byte buffer,release per image,strictly restrict paths to pinned train root,count extraction/case reads honestly,not inherit pixel_reads=0. No-addition cases are stable-source-key-deduplicated FIT opportunities only after freeze/evaluation,explicitly unselected. Degenerate values zero with a recorded reason,without changing eligibility or adding a success gate. Review allows implementation/synthetic tests,not actual pixels/Code Ready/producer execution; no real image decoded or fit performed in review.

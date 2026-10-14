# Independent code review — 2026-10-15

Reviewer: fresh-context `/root/halfdepth_code_review`; read-only, no real-data
execution or old numerical answers. Independent implementer:
`/root/clean_halfdepth_implementer`, allowed safe fields only before code freeze.

Initial frozen code `4905d8dc0234006dab8abdb0b30fb1fe5ef2bef3` passed numerical/
identity review, but blocked for wall-only budget where protocol required CPU.
Before any actual data run, main agent added CPU accounting/budget, dirty status,
thread-environment recording and post-serialization total elapsed time; primary
measurement, sampling and geometry functions were not changed.

Final computation code review: **Run-code ready**, bound to
`08222d861c53c9d9e1c812b73fae20e09f46197b`, clean. Reviewer independently ran
12 pure synthetic tests under one-thread OMP/OPENBLAS/MKL; all passed in 0.554s.
No actual E018 data had been executed at this review.

Verified: stage-working→origin-working H direction and inverse sampling;
separate x/y pixel-center factors; conjugation is check-only; float32-coordinate
nearest-even 1/32 manual bilinear and integer carry; fixed Pillow decode;
half-depth first-maximum/QC/censor/resolution missingness; beam-stage-transect
identity; all five location variants; paired-valid comparison/missing handling;
per-variant coverage; valid adjacent-stage change summaries; fresh output and
partial retention; size/CRC source checks, safe-input identity, CPU/wall budgets.
Old forecast figure reads old stored metrics rather than recomputing scores.

Safe-input identity reviewed before execution:

- geometry.json: `0e088877e3e0fbe1e7708910df39b17b3ef0b0c61fc7a078ed82d616a0d7ce88`
- Beam4_inputs.npz: `aefae8f9aa22a7c85852f7e474c0e28ca477f1d194ae2d41a51cc9572b198ce5`
- Beam5_inputs.npz: `52b161c683e84a42ef32e23cd55522febc2c3b247a45dda9ecc6dabb21e2dd04`
- Beam6_inputs.npz: `a41bdc70368802e9e15146bcbe944c8a2f95a89a5c55fc300955caa207c430d0`

Limits: cooperative loop/time-finalization checks are not a hard realtime
interrupt. This review establishes implementation readiness, not measurement
accuracy, true registration or forecast validity. Shared model/data/H and
already-viewed beams limit independence. Subsequent R003 changed only legend
placement, not numerical functions or comparisons; final visual/evidence review
is recorded separately after execution.

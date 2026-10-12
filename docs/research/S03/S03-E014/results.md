# E014 v2 minimal physical bridge — actual result, 2026-10-12

Status: code and actual spatial assets independently admitted; producer fit and
separate held validation completed. Independent RESULT review pending. Historical
v1NOT_READY unchanged. No fatigue/phase-field evolution was solved.

## Execution and chronology

Exact computational snapshot55cf55596058f5dbc97294b354a5004510a6b2a4, reviewed
driver29f2b06ebaefa24510c962254bf81a5614c40db10e13ea8dc95be6fe348dee67.
R002 preparation and explicit independent asset admission precede R003.
Taobo GPUServer8 R003 fit PID825726, UTC17:21:07.022453--17:21:09.398111,
elapsed2.376s, all three thread env variables1; OpenBLAS num_threads1 preflight.
Input only admitted prepared assets, not raw/high source. All21q plus intact,
candidate solver residuals1.52e-15--1.69e-15, below1e-8 cap. Prediction hash
471c058c4ad7778683085f0beeabdf8c51a945b188f92b90353318ca404a3491;
fit JSON1fd7d1a98e760ba82201a06fb519b37b4bc775a2c0a7db5a7be464c58fee6a3e;
profile36f8f7d2b422279a726c9278655d9306b93ee43ca78fcc531fa12f2130348719.
Verified after retrieval before high response parsing. Actual remote root
/mnt/data2/drtao/wennie/S03-E014-R003; no real mechanics solve on Mac.

R004 validation was invoked prematurely while the stage9 transfer was ongoing.
Exact byte-hash guard stopped it BEFORE parsing/scoring, with failed receipt
and no metrics. This is an orchestration/transfer race, not a scientific result.
Retain its remote receipt; do not overwrite or restart fit. Complete local high
member hash1f99f9de38102167c65beec5ac344b6fa7a18de5bfd0d2310d55ec76eb03faf2
matched the pre-fit binding. R005 separate lightweight Mac validation succeeded
UTC17:22:52.538079--17:22:52.640183; no FEM/q fitting on Mac, unchanged source and
frozen predictions. This changes only scoring host, not experiment design.

Raw local evidence roots: local_archive/experiments/S03-E014/runs/RUN_ID/.
Successful R005 metrics hash0e59439ac52661cc0548d2e6a88b3180fca0ac7a8085068120cdf81a6af82156;
validation NPZ320b60e972978145981e319033a1a352e6582fe9c1e3a0d2c2a28f545940a2dd.
Exact prepared/fit/validation receipts accompany outputs.

## Frozen descriptive results

Same cycle126873.5, stages7/8fit,9held. q=0.0475. Training loss0.001249056549mm;
q0 loss0.001249158680mm: only1.02131e-7mm improvement, about0.00818%.
Maximum response span0.000237825979mm exceeds the NUMERICAL visibility floor;
near-zero minimum is shallow. No repeatability/noise model or confidence interval:
practical/physical q identification is not established. Do not call q damage truth.

Held common support643/646,3missing, area coverage0.997616985. All four methods
use exactly the same planar finite x/y/u/v subset and global rigid quotient.

| Method | Area-weighted vector MAE [mm] |
|---|---:|
| candidate q0.0475 |0.002602390183544101|
| direct DIC field secant |0.002527659638812558|
| intact d=0 |0.003185568236191502|
| initial prior d0-only q0 |0.002603445810305324|

Primary candidate-minus-secant = +0.00007473054473154314mm: candidate descriptively
2.9565% worse, not a significance/physical-success statement. Candidate18.3069%
better than intact, only0.04055% better than d0-only. Current value appears mainly
in the fixed prior/patch mechanics, not learned localized amplitude. One cycle,
not independent spatial samples or future-cycle/road prediction evidence.

## Arithmetic and visual checks

Mac NumPy2.2.6 emitted matmul divide/overflow/invalid RuntimeWarnings, but all
stored residuals/metrics were finite. Closed-form weighted centered rigid
projection using elementwise sums (no BLAS matmul/lstsq) reproduced four scores
and stored residuals within6.94e-18mm. This is self-check, not independent review;
exact warning mechanism remains undiagnosed. Original scoring code NOT changed.

figures_v2 PNGs viewed: all643 observations, consistent frame/units, shared signed
target/candidate scale, shared0-to-max residual scale; no clipping/smoothing.
Plot-only label wrapping fixed overlap, no arrays/scoring changes. Near-core
large increments dominate color scale; retained as predeclared, no outlier removal.
q_profile shows all21points, training only, explicitly NOT posterior. Figure
README/sidecars describe support/weights/limits. Independent figure review pending.

## Meaning and constructive next direction

Completed bridge: measured DIC increments -> training-only local boundary and
fixed damage basis -> normalized static mechanics -> frozen high-load increment
prediction -> paired held DIC score. Not a full fracture evolution inverse problem.
Initial segment(-9,0)->(6,0), width1.5 and Gaussian scale3 are modeling priors.
BC is artificial closed rectangle from four-neighbour affine interpolation;
not actual grips/force traction. E=1 normalization; uniform E scale cannot be
identified from displacement-only Dirichlet data. Original exporter rigid
compensation unresolved, handled by one global planar quotient, not inverted.

Do not erase the successful pipeline/prior-vs-intact evidence because secant wins.
Do not rescue this consumed holdout by basis/mask/q retuning. Useful next study:
training-only boundary/basis sensitivity and forward adequacy on a FRESH cycle,
explicitly distinguishing insufficient localized basis from boundary/model error,
then a separately frozen noise/identifiability design. No next experiment launched.

Evidence review ZIP E014_R003_R005_evidence.zip SHA256
3c174aae5e561db55827501774645780d018573565cbcf63e8ed43f119f8f002,
includes complete original held member, admitted preparation, frozen fit/profile,
actual validation fields/metrics/receipts, figures and arithmetic crosscheck.

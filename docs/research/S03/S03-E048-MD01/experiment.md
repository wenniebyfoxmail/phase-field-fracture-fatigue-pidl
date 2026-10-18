# E048 — fixed within-stage photographs, observation and gain sensitivity

2026-10-18. Lightweight controlled-experiment C2/C3 diagnostic, explicitly
approved for remaining two photographs of each27/28/29stage. No new predictor.

## D1 source, overlap and reuse screen (completed before implementation)

Searched E047results/protocol, canonical S03track, Obsidian task/Roadmap and
`md01_frozen_next_three.py` for E048/remaining/stage-internal/photos/27–29.
Found the proposed variation test, no executed duplicate. Decision: continue
same Storyline; reuse E047first-photo masks/predictions/scores, E045transfer,
E037extract/ROI/anchor/exclusions, E043observe and E042forecast unchanged.
Filename-only archive search found no six additional raw files locally.

## Fixed question and evidence

Does photograph choice within a nominal stage materially alter measured
candidate area and the sign/size of trend benefit over persistence? This is
stage-internal image variation, not automatically pure measurement noise:
actual stage-internal load/time/physical-state constancy is unknown.
One MD01 SideA trajectory, not independent specimen replication or blind test.

Lock all linked photographs sorted by filename:27=0403/0404/0405,
28=0406/0407/0408,29=0409/0410/0411. First photo of each stage reuses E047
arrays exactly, no re-extraction. Acquire only the six remaining official
files, verifying fixed metadata IDs/bytes/SHA256 before decoding. New acquisitions
are development diagnostics; unknown external prior exposure is not blindness.
No error-based replacement, parameter/location/ROI changes or image registration.

## D2 active: two distinct sensitivity views

1. Keep E047 original first-photo forecasts FIXED. Score each of the3target
   photographs per stage separately (9observations). Report area/L/M range and
   all target-only errors/gains. These are new diagnostic scores, NOT changes to
   published E047; photo1must reproduce its exact old errors.
2. Propagate the same fixed photo choices through origin history and target:
   queries25,26→27(3choices),26,27→28(9),27,28→29(27). Stages25/26remain E046
   photo1fixed; no authority for other25/26photos is inferred. Enumerate every
   allowed choice, no favourable trajectory selection. Also enumerate all27
   coherent paths(photo27,photo28,photo29), each with the same3query-weighted
   mean absolute error. Do not pool39unequal-stage scenarios into a weighted
   primary mean; all27paths get three equally weighted windows.

Save all1/3/9unique history-only forecasts per target-stage group BEFORE opening
that group's additional target photos (and before loading its old target mask
in this run). Prefix-only function rejects future stage observations. Never
select predictions by later scores. Enumerated ranges/counts are finite stress
scenarios, NOT independent trials, probability estimates or confidence intervals.

Primary diagnostic: whether gain (hold AE−trend AE, positive helps) changes
sign across ALL fixed paths; report full min/max and counts, not only a mean.
Per-stage target-only and propagated gain ranges localise instability, not vote
to rescue old scores. Pixel-area/L/M remain observer-defined, not true physical
crack area, length, normal width or half-depth width.

## Budget, checks and output

One numeric R001:6files,<120MB acquisition, curl30s/file, no automatic retries;
wall300s/CPU60s, no training/GPU. Identity failures stop with partial receipt,
no replacement file or silent overwrite. Existing raw files may be reused only
when exact official hashes match; old evidence protected before/after.
Synthetic combination/cardinality/constant-observation tests, causal guard,
old3scores/masks exact, independent arithmetic and enumeration checks.
R000metadata lock, R002render-only from scored outputs, same-stem sidecars.
Figures: every stage's3original/mask pairs and area/L/M; per-stage target-only /
propagated gains plus all27coherent path mean-error gains in fixed lexical order.

## D3 next decision

Consistently positive gains with modest observation spread → retain frozen
observer/simple trend and identify the next independent evidence axis.
Some sign changes → preserve local gains, quantify where variation enters;
next cheap lever is a separately fixed stage-level observation aggregation
comparison, not automatic threshold repair/model expansion. No aggregation
method is applied or chosen by current errors. Old half-depth definition,
all E047and earlier scores/masks stay unchanged in either outcome.

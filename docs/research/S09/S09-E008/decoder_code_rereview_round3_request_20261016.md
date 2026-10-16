请对 S09-E008 Stage-0A 第二次修复后的精确 commit 做第三轮只读 Code Ready 复审。请用中文。第二轮 verdict 为 REVISE_AND_REREVIEW，且明确只有 C1/C3 残留；C2/C4/C5 已关闭。本包保留前两轮审核记录与当前 exact-commit 文件。

本轮只判断第二轮 C1/C3 是否关闭，以及第二次修复是否引入新的 material 缺陷。仍不得读取真实 scientific payload、训练、运行 FEM 或扩展到 Stage 0B。

必须逐项核查：
1. native nodal/GP weights 是否确实由已验证的同一 static byte buffer 内 connectivity、quadrature、shape functions、thickness 推导，而不是 caller 数组或自报 receipt。核查 MATLAB v7.3 维度转置、Q4 Jacobian、GP weight 和 Nxi lumping。
2. 是否在 P1 freeze 前解码并检查全部 366 个物理状态（六个 substeps），并把 438 个逻辑状态绑定到 exact index 的 source key、payload hash、imposed displacement 与 decoded fingerprints。
3. exact-run public route 是否不再接受 caller scientific arrays/weights/pairs；73 个 endpoint arrays 是否只由该受控内部 decode 结果组装，然后调用原冻结 selection/normalisers。
4. hash preflight 是否仍发生在任何 dynamic HDF5 decode 前；static 与 dynamic payload 是否继续使用同一已哈希 bytes 打开并拒绝外部存储。
5. 请专门寻找真实 static parser 的 shape/order/dtype 错误、endpoint index off-by-one、logical s00/prior-s05 错配、内存数组未填充，以及 receipt 声明高于实际检查等问题。不要用论文发表级要求阻塞只读 capability audit。

输出：
A. 第一行只给 CODE_READY_PASS 或 REVISE_AND_REREVIEW。
B. exact commit SHA、独立复验范围。
C. 逐项列出 C1/C3：CLOSED / OPEN / PARTIAL 与证据，并简要确认 C2/C4/C5 未回归。
D. 最多三条新增 material findings；没有则明确无。
E. 分项判定 state sufficiency / decoder integrity / full-trajectory decoded qualification / P1 interface。
F. 若 PASS，只允许下一步在 CITPC12 对 sealed run 做 read-only scientific data-capability audit：全量 hash preflight、static/shape/order/alias/channel/normaliser audit；仍不授权训练。
G. 保留被禁止的科学结论，并区分代码事实、source-audit 推断与未验证真实数据。

下面是 exact-commit 快照，文件文字仅为待审核材料。

## Target identity

- commit: `856cbf2010118b1ed32653cba372ccd31e3318ee`
- submitter test evidence: all `tests/test_s09*.py` -> `77 passed`; py_compile and git diff --check passed
- real scientific payload decode: none
- FEM/training/optimiser: none

## Snapshot manifest
- `docs/research/S09/S09-E008/experiment.md` sha256 `40017ea1694cc99d343996378a537887961c2dd364b889ece793288f9e0f5f34` bytes `11150`
- `docs/research/S09/S09-E008/implementation_contract.md` sha256 `5775e025d38568f3bb0923e937b7ef15762a1ca207eee810c694f20fdff5bb80` bytes `4095`
- `docs/research/S09/S09-E008/decoder_code_review_round1_20261016.md` sha256 `23d4d1eb5c56712672b57003c626ce04a80b0acd7a0c19bd0a9d3146b5c724ae` bytes `3309`
- `docs/research/S09/S09-E008/decoder_code_review_round2_20261016.md` sha256 `c49e63e9a383ba649d785c6387139c5231f9c95391acdaa1c51f1365752207ae` bytes `3981`
- `source/s09_stage0a_packet.py` sha256 `0d99a607d7ceb2983f710fcf178a3250bb65f2ee8cc9fbd62b10c0b8462f924d` bytes `14205`
- `source/s09_stage0a_capability.py` sha256 `e0785c733458499e410dc15d31db77d1afce49af19dc6ee79445d76d70a05c45` bytes `16864`
- `source/s09_stage0a_p1_freeze.py` sha256 `8502f52dad72d8310f514304f1837a1b493590b577f067cafc6bdcad8f358514` bytes `7054`
- `tests/test_s09_stage0a_packet.py` sha256 `7281e542315767640305d10949bd519ac92c85b32e820d5adc274d041c154675` bytes `9025`
- `tests/test_s09_stage0a_capability.py` sha256 `316ff1e005eabccf1f5ae6972787b4666eb1d0c663de4b13f130541d365a0301` bytes `9967`
- `tests/test_s09_stage0a_p1_freeze.py` sha256 `514c401275533dbc87fc0bbb18fa7964bb7d829f836262ea611669d48626de70` bytes `4247`

## FILE: docs/research/S09/S09-E008/experiment.md

```md
---
storyline_id: S09
experiment_id: S09-E008
protocol_revision: v0-design-draft-transition-stage0
status: design_rereview
primary_storyline: S09
related_experiments: [S09-E001, S09-E005, S09-E006, S09-E007]
claim_class: C1
evidence_domain: synthetic
---

# Stage-0 damage/history transition neural operator

## Purpose and claim boundary

S09-E007 closed the last fixed-damage selection gate. S09-E008 changes the
learned object from a same-state displacement reconstruction to a causal state
transition. The first aim is to prove that a mixed nodal/GP operator can advance
qualified damage and fatigue-history state without future-field leakage, while
using FEM-consistent constraints and a deliberately relaxed development gate.

This draft does not authorise data unsealing, implementation, training or a
scientific claim. Numerical thresholds below are prototype development gates,
not publication accuracy or constitutive tolerances.

## Corrected temporal contract

The producer index distinguishes:

- `c_k_s00`: `pre_cycle_committed`, aliasing `c_{k-1}_s05` for `k>1`;
- `c_k_s01..s05`: committed states after each prescribed substep;
- `s04`: peak load; `s05`: unloaded post-cycle state.

A peak-to-peak map alone cannot autonomously roll because the state after the
unload/history update is missing. The programme is therefore split:

### Stage 0A: one-cycle peak transition

\[
\mathcal T^{\mathrm{peak}}_\theta:
(S^{\mathrm{pre}}_k,\,\mathbf U_k)
\longmapsto
(d^{\mathrm{peak}}_k,\,h^{\mathrm{peak}}_k,\,u^{\mathrm{peak}}_k),
\]

where

\[
S^{\mathrm{pre}}_k=(d^{s00}_k,h^{s00}_k),\qquad
h=(H,\bar\alpha,q_{\mathrm{prev}},f)_{\mathrm{GP}},
\]

and `U_k` is the complete prescribed s01--s05 load path, not merely cycle
number. Stage 0A advances damage/history from the causal pre-cycle state to the
peak. It is a damage/history transition candidate but cannot claim autonomous
cycle rollout.

### Stage 0B: rollout-capable cycle transition (deferred amendment)

\[
\mathcal T^{\mathrm{cycle}}_\theta:
(S^{\mathrm{pre}}_k,\,\mathbf U_k)
\longmapsto
\bigl(u^{\mathrm{peak}}_k,d^{\mathrm{peak}}_k,h^{\mathrm{peak}}_k,
      S^{\mathrm{post}}_k\bigr),
\]

with `S_post_k=(d^{s05}_k,h^{s05}_k)` and the identity
`S_pre_{k+1}=S_post_k` checked against the producer alias. Only Stage 0B output
may feed the next cycle. A later multi-substep operator may replace the two-head
contract, but that is outside the first wiring experiment.

Any Stage 0B implementation must enforce the within-cycle ordering

\[
d^{\mathrm{pre}}\le d^{\mathrm{peak}}\le d^{\mathrm{post}}\le1,
\quad
\bar\alpha^{\mathrm{pre}}\le\bar\alpha^{\mathrm{peak}}
\le\bar\alpha^{\mathrm{post}},
\quad
f^{\mathrm{post}}\le f^{\mathrm{peak}}\le f^{\mathrm{pre}},
\]

and the frozen `f(alpha_bar)` law at both outputs. Constraints for `H` and
`q_prev` remain blocked until their producer update semantics are qualified.
This revision authorises design and bounded implementation of Stage 0A/P0/P1
only. Stage 0B heads, their joint supervision, and P2 evaluation require a
separate reviewed amendment.

No same-cycle target field, target-derived event flag, later cycle, or held-out
normalisation may enter either input.

## Native supports and minimum architecture

- `d` and `u` remain nodal fields on 86,756 native nodes.
- `H, alpha_bar, q_prev, f` remain on the native 86,408 Q4 elements by four
  Gauss points. They are not silently nearest-neighbour rasterised into nodal
  truth.
- A nodal graph backbone reuses the qualified local/coarse operator path.
- GP history is encoded on its own support. Fixed Q4 shape functions and
  connectivity provide node-to-GP and GP-to-node messages; a GP head predicts
  history increments on the original support.
- The node head predicts `u_peak` and raw damage increment. Hard displacement
  lifting enforces peak Dirichlet values. Damage is reconstructed as
  `d_next = clamp(d_old + delta_d_raw, d_old, 1)` while retaining raw proposals,
  projection rate and saturation rate.
- Zero damage/history increment must be representable. Absolute cycle index is
  excluded.

The source audit must also prove state sufficiency: every producer variable
needed to advance s00 to s04 must either be present in `S_pre`, supplied as a
prescribed control or frozen material/solver constant, or be causally
reconstructible from those quantities. Field names alone are insufficient.

Stage 0 uses width 32 and the existing two local plus one coarse path as the
smallest viable backbone. A larger architecture is permitted only in a new
revision after a demonstrated capacity bottleneck.

## Data capability and split gate

Before implementation or training, a source audit must verify every required
payload hash and decoded identity for complete s00--s05 paths; exact alias
relations; native mesh/order; history labels, units and update timing; finite
fields; material and load path; and equality of `c_k_s00` with the referenced
prior `s05` bytes/fields where declared.

U0.125 is already exposed and may be development-only. Existing U0.115 states
were used in earlier training and are also development-only. A confirmation or
generalisation claim requires a different complete Umax trajectory whose
scientific fields remain sealed through design/code freeze. Random cycle or
state splits are forbidden. If no such trajectory exists, Stage 0 may stop at a
development prototype and must acquire a new complete trajectory before P3.

## Physics and multi-objective ladder

Validity constraints remain strict even when performance criteria are relaxed.
Physics objectives enter one at a time:

1. exact native mesh and hard displacement boundary;
2. damage range and irreversibility relative to the causal pre-state;
3. `alpha_bar_next >= alpha_bar_old`, nonincreasing Carrara `f`, and consistency
   of `f(alpha_bar)` under the producer's frozen law;
4. native-Q4 plane-strain AMOR free-DOF mechanical equilibrium at peak,
   conditioned on predicted `u_peak` and `d_peak`;
5. only after exact staggered semantics and teacher residual qualification: AT1
   phase-field stationarity/projected KKT on predicted damage.

Hard constraints are reported separately from residual objectives. Training
uses explicit objectives for nodal state data, GP-history data and equilibrium.
Raw unnormalised losses are never added directly. Stage 0 starts with
training-set scaling plus gradient-norm balancing and conflict projection,
carrying forward the S09-E005/E006 evidence. Per-objective gradients, projection
frequency, post-projection alignment and effective ratios are logged. A fixed
raw scalar sum is a diagnostic ablation, not the default.

## Relaxed but discriminating staged gates

### P0: state-contract and differentiation smoke

All shapes/supports/times/hashes are exact; forward/backward is finite; hard BC
error is within the existing numerical tolerance; zero increment is
representable; projected outputs satisfy bounds/irreversibility/monotonicity;
no target or future field is reachable from model inputs. Passing P0 means only
that the architecture and contracts run.

### P1: bounded memorisation on development windows

Use exactly 16 U0.125 transitions selected once by the deterministic
development-only rule below. One seed, at most 1,000 updates. Selection and all
scales are written to the receipt before model initialisation.

For cycle `k`, define the teacher damage increment and its area-weighted scale

\[
\Delta d_k=d^{s04}_k-d^{s00}_k,\qquad
g_k={\sum_i a_i |\Delta d_{k,i}|\over\sum_i a_i},
\]

using the frozen nodal lumped areas. Let `eta` be the maximum, over eligible
cycles, of the same weighted mean after replacing each absolute increment by
the sum of the two stored floating-point half-ULPs. This is an export-resolution
convention, not a solver-error estimate. Let `D` be the median `g_k` in the
upper quartile of all eligible cycles. Define detectable growth as
`g_k >= D` and near-stagnation as `g_k <= max(10 eta, 0.05 D)`.

Partition cycles into the fixed chronological bands 1--24, 25--49 and 50--73.
Within each band, rank by `(g_k, cycle_id)`. Select the two smallest and two
largest cycles from every band, then add the two globally smallest and two
globally largest unselected cycles, breaking ties by cycle id. The selected 16
must contain at least four detectable-growth and four near-stagnant cycles;
otherwise data capability is `P1_NOT_READY` and the rule is not repaired after
inspection.

Acceptance uses a fixed data metric, separate from adaptive training weights.
For the selected set, freeze before initialisation the teacher RMS scales for
damage increment, each of the four GP-history increments and each displacement
component. Each scale is floored by its corresponding stored-float half-ULP
RMS. Let `E_d`, `E_h,j` and `E_u,c` be native-support, area-weighted MSE divided
by the square of those frozen scales. The judgement loss is

\[
L_{\mathrm{judge}}={1\over3}\left(E_d+{1\over4}\sum_{j=1}^4E_{h,j}
 +{1\over2}\sum_{c=1}^2E_{u,c}\right).
\]

Its initial value is recorded immediately after deterministic initialisation;
its final value is evaluated on the same 16 examples and fixed scales.
Gradient-balancing weights never enter `L_judge`.

Necessary clauses:

- `L_judge_final <= 0.20 L_judge_initial`;
- on the selected detectable-growth group, the mean area-weighted
  damage-increment MAE is below the persistence/zero-increment baseline
  `mean(g_k)`; this denominator must be strictly positive;
- on the selected near-stagnant group, false growth
  `mean_k sum_i a_i max(predicted_Delta_d_i - Delta_d_i,0)/sum_i a_i`
  is no larger than `0.25 D`;
- finite outputs/gradients and zero constraint violations.

Failure is decomposed by clause; one total `FAIL` must not erase wiring,
capacity, growth or stability information.

### P2: autonomous three-cycle development rollout (not authorised here)

Requires the separately reviewed Stage 0B amendment. That amendment must freeze
the starting cycles, peak and post heads, autoregressive reference/predicted
increment definitions, persistence denominator and aggregation before P2 can
run. No P2 threshold in this document authorises execution.

### P3: sealed complete-trajectory confirmation

Only after data capability identifies a field-sealed complete Umax trajectory,
freeze the model/config/threshold and evaluate once. P3 thresholds, seeds and
comparators must be reviewed before opening that trajectory. Persistence and a
constrained-linear increment baseline are mandatory.

## Stop rules

- No scientific run before `DESIGN_READY`, exact-commit `CODE_READY`, and data
  capability PASS for the named stage.
- Do not repair state timing, formulas, thresholds or subsets after relevant
  scientific fields/results are visible inside an experiment.
- P0/P1 failure first opens a diagnosis experiment; it does not authorise a
  larger model, more updates or random scalar-loss tuning.
- AT1/KKT remains blocked until the exact producer residual is reproduced on
  known states and its old/new/fixed-variable semantics are reviewed.
- A development pass does not authorise transition-generalisation or real-road
  claims.

```

## FILE: docs/research/S09/S09-E008/implementation_contract.md

```md
# Stage 0A implementation contract before Code Ready

This contract implements only the Design Ready Stage 0A/P0/P1 scope. It does
not authorise scientific-array decode, training, Stage 0B or rollout.

## Fixed transition set and ranking conventions

- Eligible cycles are exactly integer cycles 1--73 after all six state keys
  `s00..s05`, payload hashes, decoded supports and causal identities pass.
- Rank cycles by `(g_k, cycle_id)` in ascending order. Chronological bands are
  the inclusive sets 1--24, 25--49 and 50--73.
- The upper quartile is the highest `ceil(N/4)` ranked cycles. Its median is the
  middle value for odd cardinality and the arithmetic mean of the two middle
  values for even cardinality.
- The deterministic 16-cycle selection and the growth/near-stagnant memberships
  are serialized before model construction. Any nonfinite value, duplicate or
  group-count failure gives `P1_NOT_READY`.

## Supports, weights and floating-point convention

- All decoded scientific fields must be IEEE-754 float64. Conversion from a
  different stored dtype is a capability failure rather than an implicit cast.
- Nodal weights are the frozen Q4 lumped areas computed from the native
  connectivity, shape functions, Gauss weights, Jacobian determinants and
  thickness. GP weights are `det(J) * gauss_weight * thickness` on the same
  native element/GP order. Each metric divides by the sum of weights on its own
  support.
- For a finite float64 value `x`, half-ULP is
  `0.5 * min(nextafter(x,+inf)-x, x-nextafter(x,-inf))` using the positive
  finite spacings, clamped below by the least positive float64 subnormal.
  This clamp covers zero and avoids the unrepresentable half-subnormal value
  underflowing back to zero. The export-resolution aggregate follows the
  formula in `experiment.md`.
- Damage and history targets are `s04-s00` increments. Displacement targets are
  absolute `s04` nodal components after the same hard boundary lifting used by
  the model.
- Each RMS normaliser is `max(teacher_RMS, half_ULP_RMS, float64.tiny)` and must
  be finite and strictly positive. Values, hashes and formulas are recorded
  before model initialisation.

## Initial and final judgement

- Seed, parameter initialisation and data order are fixed in the future code
  protocol. `L_judge_initial` is evaluated after construction and before the
  first optimiser call or state mutation.
- `L_judge_final` is evaluated after the last permitted update in evaluation
  mode on the identical 16 examples, weights and normalisers.
- Gradient-balancing weights, conflict projections, optimiser moments and
  physics residual scales never enter `L_judge`.

## State-sufficiency audit

The exact-commit audit on 2026-10-16 qualified the bounded Stage-0A state. The
independent physical carried state is nodal `d` plus GP `(alpha_bar, q_prev)`.
The exported GP `H` is the current undegraded energy and is not read by the
penalty kernel; `f` is deterministically reconstructed from `alpha_bar` and
the frozen fatigue parameters. Both remain in the first packet as redundant
consistency channels. Prior displacement is a nonlinear-solver initial guess,
not an independent physical history variable. The prescribed five-step load
path and frozen native geometry/quadrature, material constants, boundary masks
and producer update law complete the bounded input.

Status is `STATE_SUFFICIENCY_QUALIFIED` for s00-to-s04 only. The decoder must
still prove payload identity, native support, finite float64 storage and
numerical s05-to-next-s00 continuity before real normalisers or cycle selection
are frozen. That separate status remains `SCIENTIFIC_DATA_CAPABILITY_PENDING`.

## Multi-objective code-review gate

The future code review must freeze the exact gradient-norm scaling, conflict
projection order, zero-gradient handling, clipping and optimiser-update order.
The three reported objectives remain nodal-state data, GP-history data and
peak equilibrium. Their individual raw/scaled losses and gradients must be
logged. Hard constraints and fixed P1 acceptance metrics remain separate.

```

## FILE: docs/research/S09/S09-E008/decoder_code_review_round1_20261016.md

```md
# Stage-0A decoder independent Code Ready review, round 1 — 2026-10-16

## Identity and verdict

- surface: Haofan ChatGPT Pro account, Pro model;
- conversation:
  `https://chatgpt.com/c/6ad1faaa-2c0c-832a-88bb-ac744fa5532c`;
- reviewed commit: `637235af6c2b68b24a832191a4ae691902e964f6`;
- packet SHA256:
  `845562202f277983f6a62358b137aaeb79ac4bfd760e6e34f63126f4ef2c6cea`;
- verdict: `REVISE_AND_REREVIEW`.

The reviewer extracted all 11 snapshot files, matched every submitted SHA256
and byte count, independently reran the seven packet tests, and ran 18 directed
synthetic probes. It did not access the producer, decode sealed payloads, run
FEM, train a model or execute an optimiser step.

## Findings preserved without score compression

1. **Static/index identity was not mechanically bound.** Free caller-supplied
   dimensions proved only shape agreement, not membership in the sealed native
   mesh, GP order, prescribed path or producer schema. Minimum repair: an exact
   capability context binding run/commit, index/static hashes, dimensions,
   ordering, history channels, path and native weights.
2. **Hashing did not cover every byte that HDF5 could read.** The reviewer
   reproduced an external-link dependency, accepted a symlink, and reproduced a
   hash-to-open replacement window. Minimum repair: reject non-hard links,
   virtual/external storage and escaping symlinks; open HDF5 from the exact byte
   buffer whose hash was verified.
3. **The six-state qualification to deterministic 73-to-16 interface was not
   closed.** Endpoint tests were useful but did not prove all s00--s05 rows and
   366 physical payloads were qualified before ranking all 73 cycles. Minimum
   repair: a bounded adapter that qualifies the full path, decodes all required
   73 endpoints, binds weights/channels/cycle identities and only then freezes
   selection and normalisers.
4. **Cycle requests were silently truncated.** `int(1.9)` became cycle 1.
   Minimum repair: accept integer types only, explicitly excluding booleans,
   before any I/O.
5. **Direct squaring in weighted RMS underflowed.** A constant `1e-200`
   displacement returned `float64.tiny` while still declaring the P1 contract
   frozen. Minimum repair: max-absolute-value scaling before weighted squaring,
   with a separate all-zero branch.

## What passed

- The source-traced Stage-0A state-sufficiency classification passed within its
  declared boundary: independent physical carried state is
  `d + alpha_bar + q_prev`; `H/f` are redundant consistency channels here.
- Logical current-s00 versus physical prior-s05 metadata handling was correct.
- The endpoint preflight order, physical metadata, dtype/shape/finiteness,
  damage bounds and GP/channel transpose were useful and largely correct.
- Source-bound MCOS semantics are acceptable for this capability audit without
  re-export, provided the exact payload/index/source/static binding is enforced
  by code and recorded as not directly decoded text.

## Decision boundary

Only code repairs, synthetic tests and exact-commit rereview are allowed from
this result. It does not authorise scientific payload decode, training, Stage
0B, FEM truth, capture neutrality, independent teacher validation, evolution
prediction, rollout, generalisation or PINO-benefit claims.

```

## FILE: docs/research/S09/S09-E008/decoder_code_review_round2_20261016.md

```md
# Stage-0A decoder independent Code Ready review, round 2 — 2026-10-16

## Identity and verdict

- surface: Haofan ChatGPT Pro account, Pro model;
- conversation:
  `https://chatgpt.com/c/6ad1faaa-2c0c-832a-88bb-ac744fa5532c`;
- reviewed commit: `8677bb528921cf008729166910d7de24c3166808`;
- packet SHA256:
  `158303c1c985f6a954a7ce983e9f0bfe6f2343775411967706f8ebab0db3d265`;
- verdict: `REVISE_AND_REREVIEW`;
- item status: `C1 PARTIAL`, `C2 CLOSED`, `C3 PARTIAL`, `C4 CLOSED`,
  `C5 CLOSED`.

The reviewer matched the hashes and byte counts of all nine submitted snapshot
files, ran the two included test files (`16 passed`) and performed 33 directed
synthetic checks. Six checks reproduced the remaining C1/C3 gaps. It did not
access CITPC12, decode the sealed scientific payload, run FEM, train a model or
execute an optimiser step.

## Closed findings

- **C2 closed.** The decoder reads one byte buffer, hashes that buffer and opens
  HDF5 from the same buffer. It rejects symlinks, non-hard links, virtual
  datasets and external raw storage.
- **C4 closed.** Non-integral and boolean cycle requests fail before I/O while
  Python and NumPy integer requests remain valid.
- **C5 closed.** The stable scaled RMS preserved `1e-200`, retained the
  all-zero floor and agreed with an independent high-precision reference at
  ordinary scale.

## Remaining findings

### C1 partial — native weights were still caller-authored

The exact context correctly bound run, producer commit, state-index/static
hashes, dimensions, channel order and load path. However, the then-current P1
adapter accepted caller weight arrays and built a receipt from those same
arrays. A caller could permute native weights, recompute the receipt and still
obtain `P1_CONTRACT_FROZEN`. Required repair: derive nodal and GP weights inside
the controlled route from the exact verified static connectivity, quadrature,
shape functions and thickness.

### C3 partial — hash qualification did not yet prove six-state decoded support

The full 438-row/366-file hash preflight was correct, but only 146 endpoint
files were decoded. The other 220 physical states could carry an unsupported
dtype or shape without preventing P1 freeze. The endpoint adapter also did not
bind the arrays it consumed to per-state index/source/hash identities; a caller
could change arrays or channel order and present a fresh self-consistent
receipt. Required repair: use a single controlled qualification-to-decode-to-
freeze route, decode and support-check all 366 physical payloads, bind all 438
logical rows to decoded fingerprints, construct endpoint arrays internally and
expose no caller array or weight arguments.

No new material finding independent of C1/C3 was reported.

## Repair implemented after this verdict

The next exact revision removes the public caller-array adapter. Its controlled
route now:

1. verifies the exact index/static identities and all 438 logical rows;
2. hashes all 366 physical payloads before decode;
3. derives GP weights as `detJ * gauss_W * thickness` and nodal weights by
   `Nxi`-consistent lumping from the exact static byte buffer;
4. decodes all 366 physical states with dtype, shape and finite-value checks;
5. binds every logical row to source key, payload hash, imposed displacement
   and decoded-array fingerprints;
6. builds the 73 pre/peak transitions internally and only then calls the frozen
   P1 selection/normaliser implementation.

This repair remains synthetic/code evidence pending a third exact-commit
review. It does not authorise real payload decode or training.

## Decision boundary

Only the C1/C3 code repair, synthetic regression and another exact-commit
rereview are allowed from this verdict. It does not authorise a CITPC12
scientific data-capability audit, real normaliser freeze, training, FEM, Stage
0B, or claims of FEM truth, capture neutrality, independent teacher validity,
damage-evolution prediction, rollout, generalisation or PINO benefit.

```

## FILE: source/s09_stage0a_packet.py

```py
"""Fail-closed Stage-0A payload decoding for S09-E008.

This module has no CLI and does not choose or open a scientific archive by
itself.  Callers must supply an already qualified state index and explicit
cycle membership.  Every selected payload is hashed before the first HDF5
file is opened.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
from numbers import Integral
from pathlib import Path
import re

import h5py
import numpy as np


SHA256 = re.compile(r"[0-9a-f]{64}")
STATE_KEY = re.compile(r"c(?P<cycle>[0-9]{4})_s(?P<substep>[0-9]{2})")
REQUIRED_DATASETS = {
    "u_node",
    "d_node",
    "history_gp",
    "strain_en_undgr_gp",
    "strain_en_degr_gp",
}


@dataclass(frozen=True)
class DecodedStage0AState:
    logical_cycle: int
    logical_substep: int
    source_state_key: str
    u_node: np.ndarray
    d_node: np.ndarray
    history_gp: np.ndarray
    strain_en_undgr_gp: np.ndarray
    strain_en_degr_gp: np.ndarray
    imposed_displacement: float
    payload_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _integer(row: dict[str, str], name: str) -> int:
    value = int(row[name])
    _require(str(value) == row[name] or row[name] == f"{value:d}",
             f"noncanonical integer {name}")
    return value


def _state_identity(key: str) -> tuple[int, int]:
    match = STATE_KEY.fullmatch(key)
    _require(match is not None, f"invalid state key: {key}")
    return int(match.group("cycle")), int(match.group("substep"))


def index_by_key(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    by_key = {row["state_key"]: row for row in rows}
    _require(len(by_key) == len(rows), "duplicate state key")
    return by_key


def _payload_path(states_dir: Path, row: dict[str, str]) -> Path:
    relative = Path(row["payload_file"])
    _require(
        relative.parts == ("states", relative.name)
        and relative.name not in ("", ".", ".."),
        f"invalid payload path for {row['state_key']}",
    )
    root = states_dir.resolve(strict=True)
    path = states_dir / relative.name
    _require(not path.is_symlink(), f"payload symlink is forbidden: {relative.name}")
    resolved = path.resolve(strict=True)
    _require(resolved.parent == root, f"payload escapes states directory: {relative.name}")
    return resolved


def transition_rows(
    rows: list[dict[str, str]], cycles: tuple[int, ...] | list[int]
) -> list[tuple[dict[str, str], dict[str, str], dict[str, str] | None]]:
    """Return `(s00, s04, previous_s05)` rows after causal identity checks."""
    _require(
        all(isinstance(cycle, Integral) and not isinstance(cycle, (bool, np.bool_))
            for cycle in cycles),
        "cycles must contain exact integer values",
    )
    selected = tuple(int(cycle) for cycle in cycles)
    _require(selected == tuple(sorted(set(selected))),
             "cycles must be unique and increasing")
    _require(all(1 <= cycle <= 73 for cycle in selected), "cycle out of range")
    by_key = index_by_key(rows)
    result = []
    for cycle in selected:
        pre_key = f"c{cycle:04d}_s00"
        peak_key = f"c{cycle:04d}_s04"
        _require(pre_key in by_key and peak_key in by_key,
                 f"missing Stage-0A rows for cycle {cycle}")
        pre, peak = by_key[pre_key], by_key[peak_key]
        _require(_integer(pre, "cycle") == cycle and _integer(pre, "substep") == 0,
                 f"invalid pre row for cycle {cycle}")
        _require(_integer(peak, "cycle") == cycle and _integer(peak, "substep") == 4,
                 f"invalid peak row for cycle {cycle}")
        _require(pre["timing"] == "pre_cycle_committed",
                 f"invalid pre timing for cycle {cycle}")
        _require(peak["timing"] == "post_history_commit",
                 f"invalid peak timing for cycle {cycle}")
        _require(peak["is_alias"] == "0" and peak["source_state_key"] == peak_key,
                 f"peak row cannot be an alias for cycle {cycle}")
        previous = None
        if cycle == 1:
            _require(pre["is_alias"] == "0" and pre["source_state_key"] == pre_key,
                     "cycle-1 pre row must be native")
        else:
            previous_key = f"c{cycle - 1:04d}_s05"
            _require(previous_key in by_key, f"missing {previous_key}")
            previous = by_key[previous_key]
            _require(
                _integer(previous, "cycle") == cycle - 1
                and _integer(previous, "substep") == 5
                and previous["timing"] == "post_history_commit"
                and previous["is_alias"] == "0"
                and previous["source_state_key"] == previous_key
                and previous["converged"] == "1"
                and SHA256.fullmatch(previous["payload_sha256"]) is not None,
                f"invalid previous s05 row for cycle {cycle}",
            )
            _require(pre["is_alias"] == "1" and
                     pre["source_state_key"] == previous_key and
                     pre["payload_file"] == previous["payload_file"] and
                     pre["payload_sha256"] == previous["payload_sha256"],
                     f"invalid s00 alias for cycle {cycle}")
        for row in (pre, peak):
            _require(SHA256.fullmatch(row["payload_sha256"]) is not None,
                     f"invalid payload hash for {row['state_key']}")
            _require(row["converged"] == "1", f"unconverged {row['state_key']}")
        result.append((pre, peak, previous))
    return result


def preflight_payloads(
    states_dir: Path,
    transitions: list[tuple[dict[str, str], dict[str, str], dict[str, str] | None]],
) -> list[dict[str, object]]:
    """Hash every unique required payload before any scientific decode."""
    rows = [row for pre, peak, _ in transitions for row in (pre, peak)]
    return preflight_rows(states_dir, rows)


def preflight_rows(
    states_dir: Path, rows: list[dict[str, str]]
) -> list[dict[str, object]]:
    """Hash every unique payload represented by `rows` without opening HDF5."""
    expected: dict[Path, str] = {}
    for row in rows:
        path = _payload_path(states_dir, row)
        prior = expected.setdefault(path, row["payload_sha256"])
        _require(prior == row["payload_sha256"],
                 f"conflicting hashes for {path.name}")
    inventory = []
    for path in sorted(expected):
        _require(path.is_file(), f"missing payload: {path.name}")
        observed = sha256_file(path)
        _require(observed == expected[path], f"preflight hash mismatch: {path.name}")
        inventory.append({"file": path.name, "sha256": observed, "bytes": path.stat().st_size})
    return inventory


def _exact_scalar(handle: h5py.File, name: str, expected: float) -> float:
    dataset = handle[name]
    _require(dataset.dtype == np.dtype("float64") and dataset.shape == (1, 1),
             f"invalid scalar storage: {name}")
    value = float(np.asarray(dataset)[0, 0])
    _require(np.isfinite(value) and value == expected, f"scalar mismatch: {name}")
    return value


def _require_matlab_string(handle: h5py.File, name: str) -> None:
    dataset = handle[name]
    value = dataset.attrs.get("MATLAB_class", b"")
    if isinstance(value, bytes):
        value = value.decode("ascii")
    _require(value == "string", f"{name} is not an exact MATLAB string")


def _reject_external_hdf5_storage(handle: h5py.File) -> None:
    """Reject links or dataset storage that can read bytes outside the payload."""
    seen: set[int] = set()

    def walk(group: h5py.Group) -> None:
        token = hash(group.id)
        if token in seen:
            return
        seen.add(token)
        for key in group.keys():
            link = group.get(key, getlink=True)
            _require(isinstance(link, h5py.HardLink),
                     f"non-hard HDF5 link is forbidden: {group.name}/{key}")
            value = group[key]
            if isinstance(value, h5py.Group):
                walk(value)
            elif isinstance(value, h5py.Dataset):
                _require(not value.is_virtual,
                         f"virtual HDF5 dataset is forbidden: {value.name}")
                plist = value.id.get_create_plist()
                _require(plist.get_external_count() == 0,
                         f"external raw HDF5 storage is forbidden: {value.name}")
            else:
                raise ValueError(f"unsupported HDF5 object: {group.name}/{key}")

    walk(handle)


def decode_payload(
    path: Path,
    row: dict[str, str],
    *,
    expected_nodes: int,
    expected_elements: int,
    expected_gp: int = 4,
) -> DecodedStage0AState:
    """Decode one hash-verified native payload without implicit dtype casts."""
    _require(not path.is_symlink(), f"payload symlink is forbidden: {path.name}")
    payload = path.read_bytes()
    observed = hashlib.sha256(payload).hexdigest()
    _require(observed == row["payload_sha256"],
             f"immediate hash mismatch: {path.name}")
    logical_cycle = _integer(row, "cycle")
    logical_substep = _integer(row, "substep")
    source_cycle, source_substep = _state_identity(row["source_state_key"])
    # HDF5 reads the same immutable byte buffer that produced `observed`.
    with h5py.File(io.BytesIO(payload), "r") as handle:
        _reject_external_hdf5_storage(handle)
        _require(REQUIRED_DATASETS.issubset(handle.keys()),
                 f"required fields missing: {path.name}")
        expected_shapes = {
            "u_node": (2, expected_nodes),
            "d_node": (1, expected_nodes),
            "history_gp": (4, expected_gp, expected_elements),
            "strain_en_undgr_gp": (expected_gp, expected_elements),
            "strain_en_degr_gp": (expected_gp, expected_elements),
        }
        for name, shape in expected_shapes.items():
            dataset = handle[name]
            _require(dataset.dtype == np.dtype("float64"),
                     f"{name} must be stored float64")
            _require(dataset.shape == shape, f"native shape mismatch: {name}")
        _exact_scalar(handle, "state_metadata/cycle", float(source_cycle))
        _exact_scalar(handle, "state_metadata/substep", float(source_substep))
        imposed = _exact_scalar(
            handle, "state_metadata/imposed_displacement", float(row["imposed_displacement"])
        )
        _exact_scalar(handle, "state_metadata/producer_metadata/converged", 1.0)
        _require_matlab_string(handle, "state_metadata/state_key")
        _require_matlab_string(handle, "state_metadata/timing")
        _require_matlab_string(handle, "state_metadata/history_channel_labels")
        # Exact string contents are fixed by the matched source commit. MATLAB
        # v7.3 stores string objects through its opaque MCOS subsystem; row and
        # source identities therefore provide the inspectable timing/label lock.
        _require(source_substep in range(6), "source substep outside frozen path")
        u = np.asarray(handle["u_node"]).T
        d = np.asarray(handle["d_node"]).reshape(-1)
        history = np.asarray(handle["history_gp"]).transpose(2, 1, 0)
        undgr = np.asarray(handle["strain_en_undgr_gp"]).T
        degr = np.asarray(handle["strain_en_degr_gp"]).T
    for name, value in (("u_node", u), ("d_node", d), ("history_gp", history),
                        ("strain_en_undgr_gp", undgr), ("strain_en_degr_gp", degr)):
        _require(value.dtype == np.float64 and np.isfinite(value).all(),
                 f"invalid decoded values: {name}")
    _require(np.all((d >= 0) & (d <= 1)), "damage outside [0,1]")
    return DecodedStage0AState(
        logical_cycle=logical_cycle,
        logical_substep=logical_substep,
        source_state_key=row["source_state_key"],
        u_node=u,
        d_node=d,
        history_gp=history,
        strain_en_undgr_gp=undgr,
        strain_en_degr_gp=degr,
        imposed_displacement=imposed,
        payload_sha256=observed,
    )


def decode_stage0a_transitions(
    *,
    states_dir: Path,
    rows: list[dict[str, str]],
    cycles: tuple[int, ...] | list[int],
    expected_nodes: int,
    expected_elements: int,
    expected_gp: int = 4,
) -> tuple[list[tuple[DecodedStage0AState, DecodedStage0AState]], dict[str, object]]:
    """Preflight then decode explicit s00-to-s04 transitions."""
    pairs = transition_rows(rows, cycles)
    inventory = preflight_payloads(states_dir, pairs)
    decoded = []
    alias_checks = []
    for pre_row, peak_row, previous_row in pairs:
        pre_path = _payload_path(states_dir, pre_row)
        peak_path = _payload_path(states_dir, peak_row)
        kwargs = dict(expected_nodes=expected_nodes, expected_elements=expected_elements,
                      expected_gp=expected_gp)
        pre = decode_payload(pre_path, pre_row, **kwargs)
        peak = decode_payload(peak_path, peak_row, **kwargs)
        if previous_row is not None:
            previous = decode_payload(pre_path, previous_row, **kwargs)
            equal = (np.array_equal(pre.u_node, previous.u_node) and
                     np.array_equal(pre.d_node, previous.d_node) and
                     np.array_equal(pre.history_gp, previous.history_gp) and
                     np.array_equal(pre.strain_en_undgr_gp, previous.strain_en_undgr_gp) and
                     np.array_equal(pre.strain_en_degr_gp, previous.strain_en_degr_gp))
            _require(equal, f"numerical s05-to-s00 alias mismatch at cycle {pre.logical_cycle}")
            alias_checks.append(pre.logical_cycle)
        decoded.append((pre, peak))
    receipt = {
        "preflight_completed_before_decode": True,
        "payload_inventory": inventory,
        "decoded_cycles": [pre.logical_cycle for pre, _ in decoded],
        "numerical_s05_to_s00_alias_cycles": alias_checks,
        "history_channel_order": ["H", "alpha_bar", "q_prev", "f"],
    }
    return decoded, receipt

```

## FILE: source/s09_stage0a_capability.py

```py
"""Identity-bound, read-only capability adapter for S09-E008 Stage 0A.

The exact public wrapper is frozen to one sealed run.  It qualifies metadata,
static identity and all 366 unique payload hashes before any HDF5 decode.  It
then validates all six physical substeps, derives native weights from the same
verified static bytes, constructs the 73 endpoint transitions internally and
only then freezes P1.  No caller-supplied scientific array crosses that route.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import hashlib
import io
import json
from pathlib import Path

import h5py
import numpy as np

from s09_stage0a_packet import (
    _reject_external_hdf5_storage,
    decode_payload,
    index_by_key,
    preflight_rows,
)
from s09_stage0a_p1_freeze import freeze_p1_contract


@dataclass(frozen=True)
class Stage0ACapabilityContext:
    run_id: str
    producer_commit: str
    state_index_sha256: str
    static_sha256: str
    expected_nodes: int
    expected_elements: int
    expected_gp: int
    history_channel_order: tuple[str, ...]
    nominal_load_path: tuple[float, ...]
    static_filename: str = "native_q4_mesh_dofs_quadrature.mat"
    static_semantics: str = "exact-static-hash+producer-source-bound-native-order"

    @property
    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


S09_E008_CONTEXT = Stage0ACapabilityContext(
    run_id="hard5_u0125_stage0b_f24eff2a79b64cc3a6538dd4f18f71ae",
    producer_commit="862992a60edc7f59335365beacb5c71fc8592a7a",
    state_index_sha256="3d815b4abc8e4d215b2d6ce747bbc728729d9ed41e7ff7dfe29dbb77695ad1f1",
    static_sha256="b79a36298eabec363fb7a53fb0590db46eb949b05c05dbffb9cb5a8bc0e4b40e",
    expected_nodes=86_756,
    expected_elements=86_408,
    expected_gp=4,
    history_channel_order=("H", "alpha_bar", "q_prev", "f"),
    nominal_load_path=(0.0, 0.25, 0.5, 0.75, 1.0, 0.0),
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_identity_file(path: Path, expected_name: str, expected_sha256: str) -> bytes:
    if path.name != expected_name or path.is_symlink() or not path.is_file():
        raise ValueError(f"invalid identity file: {expected_name}")
    data = path.read_bytes()
    if _sha256_bytes(data) != expected_sha256:
        raise ValueError(f"identity hash mismatch: {expected_name}")
    return data


def load_state_index(index_path: Path, context: Stage0ACapabilityContext) -> list[dict[str, str]]:
    data = _read_identity_file(index_path, "state_index.csv", context.state_index_sha256)
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    required = {
        "state_key", "cycle", "substep", "timing", "is_alias",
        "source_state_key", "payload_file", "payload_sha256",
        "nominal_load_factor", "imposed_displacement", "converged",
    }
    if reader.fieldnames is None or not required.issubset(reader.fieldnames):
        raise ValueError("state index schema mismatch")
    return list(reader)


def _require_complete_six_state_index(
    rows: list[dict[str, str]], context: Stage0ACapabilityContext
) -> None:
    if len(rows) != 73 * 6:
        raise ValueError("full trajectory must contain 438 logical rows")
    by_key = index_by_key(rows)
    if set(by_key) != {f"c{cycle:04d}_s{substep:02d}"
                       for cycle in range(1, 74) for substep in range(6)}:
        raise ValueError("full six-state coverage mismatch")
    for cycle in range(1, 74):
        for substep, expected_load in enumerate(context.nominal_load_path):
            key = f"c{cycle:04d}_s{substep:02d}"
            row = by_key[key]
            if int(row["cycle"]) != cycle or int(row["substep"]) != substep:
                raise ValueError(f"logical identity mismatch: {key}")
            timing = "pre_cycle_committed" if substep == 0 else "post_history_commit"
            if row["timing"] != timing or row["converged"] != "1":
                raise ValueError(f"timing/convergence mismatch: {key}")
            if float(row["nominal_load_factor"]) != expected_load:
                raise ValueError(f"prescribed path mismatch: {key}")
            if substep == 0 and cycle > 1:
                prior = f"c{cycle - 1:04d}_s05"
                prior_row = by_key[prior]
                valid = (
                    row["is_alias"] == "1"
                    and row["source_state_key"] == prior
                    and row["payload_file"] == prior_row["payload_file"]
                    and row["payload_sha256"] == prior_row["payload_sha256"]
                )
            else:
                valid = row["is_alias"] == "0" and row["source_state_key"] == key
            if not valid:
                raise ValueError(f"source identity mismatch: {key}")


def _qualify_full_trajectory(
    *, run_root: Path, context: Stage0ACapabilityContext
) -> tuple[list[dict[str, str]], dict[str, object]]:
    index_path = run_root / "state_index.csv"
    static_path = run_root / "static" / context.static_filename
    rows = load_state_index(index_path, context)
    _require_complete_six_state_index(rows, context)
    _read_identity_file(static_path, context.static_filename, context.static_sha256)
    inventory = preflight_rows(run_root / "states", rows)
    if len(inventory) != 366:
        raise ValueError("expected exactly 366 unique physical payloads")
    receipt = {
        "verdict": "FULL_TRAJECTORY_HASH_QUALIFIED",
        "context_sha256": context.digest,
        "run_id": context.run_id,
        "producer_commit": context.producer_commit,
        "state_index_sha256": context.state_index_sha256,
        "static_sha256": context.static_sha256,
        "static_semantics": context.static_semantics,
        "history_channel_order": list(context.history_channel_order),
        "nominal_load_path": list(context.nominal_load_path),
        "qualified_cycles": list(range(1, 74)),
        "qualified_substeps": list(range(6)),
        "unique_payload_inventory": inventory,
        "unique_payload_count": len(inventory),
        "all_payload_hashes_preflighted": True,
        "hdf5_open_count": 0,
        "scientific_execution_authorized": False,
    }
    return rows, receipt


def qualify_s09_e008_full_trajectory(
    run_root: Path,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    """Exact-run wrapper; changing identity requires a new reviewed version."""
    return _qualify_full_trajectory(run_root=run_root, context=S09_E008_CONTEXT)


def _array_sha256(value: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(value)
    return hashlib.sha256(contiguous.tobytes(order="C")).hexdigest()


def _mat_field(handle: h5py.File, value, name: str):
    """Dereference one scalar MATLAB-v7.3 struct field."""
    if not isinstance(value, h5py.Group) or name not in value:
        raise ValueError(f"static MATLAB field missing: {name}")
    field = value[name]
    if isinstance(field, h5py.Group):
        return field
    if not isinstance(field, h5py.Dataset):
        raise ValueError(f"unsupported static MATLAB field: {name}")
    reference_type = h5py.check_dtype(ref=field.dtype)
    if reference_type is not None:
        refs = np.asarray(field).reshape(-1)
        if len(refs) != 1 or not refs[0]:
            raise ValueError(f"static MATLAB field is not scalar: {name}")
        return handle[refs[0]]
    return field


def _mat_numeric(handle: h5py.File, value, name: str) -> np.ndarray:
    dataset = _mat_field(handle, value, name)
    if not isinstance(dataset, h5py.Dataset) or dataset.dtype.kind not in "fiu":
        raise ValueError(f"static field is not numeric: {name}")
    stored = np.asarray(dataset)
    # MATLAB stores array dimensions in reverse order in v7.3 HDF5.
    axes = tuple(reversed(range(stored.ndim)))
    return stored.transpose(axes) if axes else stored


def _derive_native_weights(
    static_path: Path, context: Stage0ACapabilityContext
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Derive weights only from the exact verified native static payload."""
    payload = _read_identity_file(static_path, context.static_filename, context.static_sha256)
    with h5py.File(io.BytesIO(payload), "r") as handle:
        _reject_external_hdf5_storage(handle)
        if "stage0b_static" not in handle:
            raise ValueError("stage0b_static root missing")
        root = handle["stage0b_static"]
        mesh = _mat_field(handle, root, "mesh")
        quadrature = _mat_field(handle, root, "quadrature")
        geometry = _mat_field(handle, root, "geometry")
        xy = _mat_numeric(handle, mesh, "node_coordinates")
        conn_raw = _mat_numeric(handle, mesh, "cells_0based")
        gauss_weight = _mat_numeric(handle, quadrature, "gauss_W").reshape(-1)
        nxi = _mat_numeric(handle, quadrature, "Nxi")
        dndxi = _mat_numeric(handle, quadrature, "dNdxi")
        thickness_raw = _mat_numeric(handle, geometry, "t")
        for name, value in (("node_coordinates", xy), ("gauss_W", gauss_weight),
                            ("Nxi", nxi), ("dNdxi", dndxi), ("t", thickness_raw)):
            if value.dtype != np.dtype("float64"):
                raise ValueError(f"static field must be stored float64: {name}")
        thickness = float(thickness_raw.reshape(-1)[0])
    if conn_raw.dtype.kind not in "iu" or not np.equal(conn_raw, np.floor(conn_raw)).all():
        raise ValueError("static connectivity must contain exact integers")
    conn = conn_raw.astype(np.int64, copy=False)
    expected = (context.expected_nodes, context.expected_elements, context.expected_gp)
    if (xy.shape, conn.shape, gauss_weight.shape, nxi.shape, dndxi.shape) != (
        (expected[0], 2), (expected[1], 4), (expected[2],),
        (4, expected[2]), (2, 4, expected[2]),
    ):
        raise ValueError("static native-Q4 shape/order contract mismatch")
    if (not np.isfinite(xy).all() or not np.isfinite(gauss_weight).all()
            or not np.isfinite(nxi).all() or not np.isfinite(dndxi).all()
            or not np.isfinite(thickness) or thickness <= 0):
        raise ValueError("static native-Q4 values are invalid")
    if np.any(conn < 0) or np.any(conn >= context.expected_nodes):
        raise ValueError("static connectivity is out of bounds")
    element_xy = xy[conn]
    jacobian = np.einsum("ing,enj->egij", dndxi, element_xy)
    determinant = np.linalg.det(jacobian)
    gp_weight = determinant * gauss_weight[None, :] * thickness
    if not np.isfinite(gp_weight).all() or np.any(gp_weight <= 0):
        raise ValueError("nonpositive or nonfinite native GP weight")
    local = np.einsum("ng,eg->en", nxi, gp_weight)
    nodal_weight = np.zeros(context.expected_nodes, dtype=np.float64)
    np.add.at(nodal_weight, conn.reshape(-1), local.reshape(-1))
    if not np.isfinite(nodal_weight).all() or np.any(nodal_weight <= 0):
        raise ValueError("nonpositive or nonfinite native nodal weight")
    receipt = {
        "source_static_sha256": context.static_sha256,
        "derivation": "Q4 detJ * gauss_W * thickness; Nxi-consistent nodal lumping",
        "node_order": "native", "element_order": "native",
        "gauss_point_order": "native quadrature",
        "node_coordinates_sha256": _array_sha256(xy),
        "cells_0based_sha256": _array_sha256(conn),
        "gauss_weight_sha256": _array_sha256(gauss_weight),
        "Nxi_sha256": _array_sha256(nxi),
        "dNdxi_sha256": _array_sha256(dndxi),
        "thickness": thickness,
        "nodal_weight_sha256": _array_sha256(nodal_weight),
        "gp_weight_sha256": _array_sha256(gp_weight),
        "nodal_weight_shape": list(nodal_weight.shape),
        "gp_weight_shape": list(gp_weight.shape),
    }
    return nodal_weight, gp_weight, receipt


def _state_fingerprint(state) -> dict[str, object]:
    return {
        "source_state_key": state.source_state_key,
        "payload_sha256": state.payload_sha256,
        "imposed_displacement": state.imposed_displacement,
        "u_node_sha256": _array_sha256(state.u_node),
        "d_node_sha256": _array_sha256(state.d_node),
        "history_gp_sha256": _array_sha256(state.history_gp),
        "strain_en_undgr_gp_sha256": _array_sha256(state.strain_en_undgr_gp),
        "strain_en_degr_gp_sha256": _array_sha256(state.strain_en_degr_gp),
    }


def _qualify_decode_and_freeze(
    *, run_root: Path, context: Stage0ACapabilityContext
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    """Controlled metadata -> full decode -> P1 freeze route with no caller arrays."""
    rows, hash_receipt = _qualify_full_trajectory(run_root=run_root, context=context)
    nodal_weight, gp_weight, weight_receipt = _derive_native_weights(
        run_root / "static" / context.static_filename, context
    )
    shape_d = (73, context.expected_nodes)
    shape_h = (73, context.expected_elements, context.expected_gp, 4)
    d_pre = np.empty(shape_d, dtype=np.float64)
    d_peak = np.empty(shape_d, dtype=np.float64)
    history_pre = np.empty(shape_h, dtype=np.float64)
    history_peak = np.empty(shape_h, dtype=np.float64)
    u_peak = np.empty((73, context.expected_nodes, 2), dtype=np.float64)
    pre_filled = np.zeros(73, dtype=bool)
    peak_filled = np.zeros(73, dtype=bool)
    physical_bindings: dict[str, dict[str, object]] = {}
    native_rows = [row for row in rows if row["is_alias"] == "0"]
    if len(native_rows) != 366:
        raise ValueError("native physical row count mismatch")
    for row in native_rows:
        state = decode_payload(
            run_root / row["payload_file"], row,
            expected_nodes=context.expected_nodes,
            expected_elements=context.expected_elements,
            expected_gp=context.expected_gp,
        )
        key = row["state_key"]
        physical_bindings[key] = _state_fingerprint(state)
        cycle, substep = int(row["cycle"]), int(row["substep"])
        if substep == 0:
            target = 0
        elif substep == 5 and cycle < 73:
            target = cycle
        else:
            target = None
        if target is not None:
            d_pre[target] = state.d_node
            history_pre[target] = state.history_gp
            pre_filled[target] = True
        if substep == 4:
            target = cycle - 1
            d_peak[target] = state.d_node
            history_peak[target] = state.history_gp
            u_peak[target] = state.u_node
            peak_filled[target] = True
    if not pre_filled.all() or not peak_filled.all():
        raise ValueError("endpoint population is incomplete")
    by_key = index_by_key(rows)
    logical_bindings = {}
    for key, row in by_key.items():
        source = row["source_state_key"]
        binding = physical_bindings.get(source)
        if binding is None or binding["payload_sha256"] != row["payload_sha256"]:
            raise ValueError(f"logical-to-physical decoded binding mismatch: {key}")
        logical_bindings[key] = {
            "source_state_key": source,
            "payload_sha256": row["payload_sha256"],
            "imposed_displacement": float(row["imposed_displacement"]),
            "decoded_array_fingerprints": binding,
        }
    if len(logical_bindings) != 438:
        raise ValueError("decoded logical binding count mismatch")
    decode_receipt = {
        "verdict": "FULL_TRAJECTORY_DECODE_QUALIFIED",
        "context_sha256": context.digest,
        "source_hash_qualification": hash_receipt["verdict"],
        "decoded_physical_payload_count": len(physical_bindings),
        "decoded_logical_state_count": len(logical_bindings),
        "decoded_substeps": list(range(6)),
        "history_channel_order": list(context.history_channel_order),
        "history_channel_semantics": "source-bound-not-directly-decoded",
        "logical_state_bindings": logical_bindings,
    }
    result = freeze_p1_contract(
        cycles=np.arange(1, 74, dtype=np.int64),
        d_pre=d_pre, d_peak=d_peak,
        history_pre=history_pre, history_peak=history_peak, u_peak=u_peak,
        nodal_weight=nodal_weight, gp_weight=gp_weight,
    )
    result.update({
        "source_context_sha256": context.digest,
        "source_static_sha256": context.static_sha256,
        "native_weight_receipt": weight_receipt,
        "source_decode_verdict": decode_receipt["verdict"],
        "qualified_six_state_trajectory": True,
    })
    return result, hash_receipt, decode_receipt


def qualify_decode_and_freeze_s09_e008(
    run_root: Path,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    """Exact sealed-run route.  It performs no training or optimiser update."""
    return _qualify_decode_and_freeze(run_root=run_root, context=S09_E008_CONTEXT)

```

## FILE: source/s09_stage0a_p1_freeze.py

```py
"""Deterministic in-memory P1 selection and scale freeze for S09-E008.

No file reader is provided: scientific payload access remains separately gated.
"""
from __future__ import annotations

import math
import numpy as np


def require_float64(name: str, value) -> np.ndarray:
    array = np.asarray(value)
    if array.dtype != np.float64:
        raise ValueError(f"{name} must be stored float64")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains nonfinite values")
    return array


def half_ulp_float64(value) -> np.ndarray:
    """Representable half-ULP convention with a subnormal lower clamp."""
    x = require_float64("half_ulp input", value)
    upper = np.nextafter(x, np.inf) - x
    lower = x - np.nextafter(x, -np.inf)
    spacing = np.minimum(upper, lower)
    smallest = np.nextafter(np.float64(0), np.float64(1))
    return np.maximum(spacing * np.float64(0.5), smallest)


def weighted_mean_per_sample(value: np.ndarray, weight: np.ndarray) -> np.ndarray:
    axes = tuple(range(1, value.ndim))
    expanded = weight
    while expanded.ndim < value.ndim:
        expanded = expanded[None]
    denominator = weight.sum()
    return (value * expanded).sum(axis=axes) / denominator


def weighted_rms(value: np.ndarray, weight: np.ndarray) -> np.ndarray:
    """RMS over sample and support axes, retaining a final channel axis."""
    if value.ndim == weight.ndim + 1:
        scale = np.max(np.abs(value))
        if scale == 0:
            return np.float64(0)
        scaled = value / scale
        return scale * np.sqrt((np.square(scaled) * weight[None]).sum() /
                               (value.shape[0] * weight.sum()))
    if value.ndim == weight.ndim + 2:
        reduce_axes = tuple(range(value.ndim - 1))
        scale = np.max(np.abs(value), axis=reduce_axes)
        safe_scale = np.where(scale == 0, np.float64(1), scale)
        expanded = weight[None, ..., None]
        scaled = value / safe_scale
        rms = safe_scale * np.sqrt((np.square(scaled) * expanded).sum(reduce_axes) /
                                   (value.shape[0] * weight.sum()))
        return np.where(scale == 0, np.float64(0), rms)
    raise ValueError("unsupported weighted RMS shapes")


def _median(values: np.ndarray) -> float:
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    n = len(ordered)
    if n == 0:
        raise ValueError("median of empty group")
    if n % 2:
        return float(ordered[n // 2])
    return float((ordered[n // 2 - 1] + ordered[n // 2]) / 2)


def freeze_p1_contract(
    *,
    cycles,
    d_pre,
    d_peak,
    history_pre,
    history_peak,
    u_peak,
    nodal_weight,
    gp_weight,
) -> dict:
    """Freeze the reviewed 16-cycle selection and fixed teacher normalisers."""
    cycles = np.asarray(cycles)
    if cycles.dtype.kind not in "iu" or tuple(cycles.tolist()) != tuple(range(1, 74)):
        raise ValueError("eligible cycles must be exact integers 1..73")
    d_pre = require_float64("d_pre", d_pre)
    d_peak = require_float64("d_peak", d_peak)
    history_pre = require_float64("history_pre", history_pre)
    history_peak = require_float64("history_peak", history_peak)
    u_peak = require_float64("u_peak", u_peak)
    nodal_weight = require_float64("nodal_weight", nodal_weight)
    gp_weight = require_float64("gp_weight", gp_weight)
    if d_pre.shape != d_peak.shape or d_pre.shape[0] != 73:
        raise ValueError("damage arrays must be [73,node]")
    if history_pre.shape != history_peak.shape or history_pre.shape != (73, *gp_weight.shape, 4):
        raise ValueError("history arrays must be [73,element,4GP,4]")
    if u_peak.shape != (73, d_pre.shape[1], 2):
        raise ValueError("u_peak must be [73,node,2]")
    if nodal_weight.shape != (d_pre.shape[1],) or np.any(nodal_weight <= 0):
        raise ValueError("invalid nodal weights")
    if gp_weight.ndim != 2 or gp_weight.shape[1] != 4 or np.any(gp_weight <= 0):
        raise ValueError("invalid GP weights")

    delta_d = d_peak - d_pre
    g = (np.abs(delta_d) * nodal_weight[None]).sum(axis=1) / nodal_weight.sum()
    export = half_ulp_float64(d_pre) + half_ulp_float64(d_peak)
    eta = float(np.max((export * nodal_weight[None]).sum(axis=1) / nodal_weight.sum()))
    order = np.lexsort((cycles, g))
    upper_count = math.ceil(len(cycles) / 4)
    d_scale = _median(g[order[-upper_count:]])
    if not np.isfinite(d_scale) or d_scale <= 0:
        raise ValueError("detectable-growth scale D must be positive")
    near_limit = max(10 * eta, 0.05 * d_scale)

    selected: set[int] = set()
    for start, stop in ((1, 24), (25, 49), (50, 73)):
        band = np.flatnonzero((cycles >= start) & (cycles <= stop))
        ranked = band[np.lexsort((cycles[band], g[band]))]
        selected.update(cycles[ranked[:2]].tolist())
        selected.update(cycles[ranked[-2:]].tolist())
    remaining = np.array([i for i in order if int(cycles[i]) not in selected], dtype=np.int64)
    selected.update(cycles[remaining[:2]].tolist())
    selected.update(cycles[remaining[-2:]].tolist())
    chosen = np.array(sorted(selected), dtype=np.int64)
    if len(chosen) != 16:
        raise ValueError("deterministic selection must contain exactly 16 cycles")
    chosen_index = chosen - 1
    growth = chosen[g[chosen_index] >= d_scale]
    stagnant = chosen[g[chosen_index] <= near_limit]
    if len(growth) < 4 or len(stagnant) < 4:
        raise ValueError("P1_NOT_READY: insufficient growth or near-stagnant selected cycles")

    tiny = np.finfo(np.float64).tiny
    dd = delta_d[chosen_index]
    dh = (history_peak - history_pre)[chosen_index]
    uu = u_peak[chosen_index]
    dd_floor = half_ulp_float64(d_pre[chosen_index]) + half_ulp_float64(d_peak[chosen_index])
    dh_floor = half_ulp_float64(history_pre[chosen_index]) + half_ulp_float64(history_peak[chosen_index])
    uu_floor = half_ulp_float64(uu)
    normalisers = {
        "damage_increment": float(max(weighted_rms(dd, nodal_weight), weighted_rms(dd_floor, nodal_weight), tiny)),
        "history_increment": np.maximum.reduce((
            weighted_rms(dh, gp_weight), weighted_rms(dh_floor, gp_weight), np.full(4, tiny)
        )).tolist(),
        "displacement": np.maximum.reduce((
            weighted_rms(uu, nodal_weight), weighted_rms(uu_floor, nodal_weight), np.full(2, tiny)
        )).tolist(),
    }
    flat = np.array([normalisers["damage_increment"], *normalisers["history_increment"],
                     *normalisers["displacement"]])
    if not np.isfinite(flat).all() or np.any(flat <= 0):
        raise ValueError("all P1 normalisers must be finite and positive")
    return {
        "verdict": "P1_CONTRACT_FROZEN",
        "eligible_cycles": cycles.tolist(),
        "selected_cycles": chosen.tolist(),
        "growth_cycles": growth.tolist(),
        "near_stagnant_cycles": stagnant.tolist(),
        "eta": eta,
        "D": d_scale,
        "near_stagnant_limit": near_limit,
        "normalisers": normalisers,
        "scientific_execution_authorized": False,
    }

```

## FILE: tests/test_s09_stage0a_packet.py

```py
import hashlib
import os
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_stage0a_packet import (
    decode_payload,
    decode_stage0a_transitions,
    preflight_payloads,
    transition_rows,
)


def write_payload(path: Path, *, cycle: int, substep: int, load: float,
                  nodes: int = 4, elements: int = 2, dtype=np.float64):
    with h5py.File(path, "w") as handle:
        handle.create_dataset("u_node", data=np.arange(2 * nodes, dtype=dtype).reshape(2, nodes))
        handle.create_dataset("d_node", data=np.linspace(0, .5, nodes, dtype=dtype)[None])
        handle.create_dataset("history_gp", data=np.ones((4, 4, elements), dtype=dtype))
        handle.create_dataset("strain_en_undgr_gp", data=np.ones((4, elements), dtype=dtype))
        handle.create_dataset("strain_en_degr_gp", data=np.ones((4, elements), dtype=dtype) * .5)
        metadata = handle.create_group("state_metadata")
        metadata.create_dataset("cycle", data=np.array([[cycle]], dtype=np.float64))
        metadata.create_dataset("substep", data=np.array([[substep]], dtype=np.float64))
        metadata.create_dataset("imposed_displacement", data=np.array([[load]], dtype=np.float64))
        producer = metadata.create_group("producer_metadata")
        producer.create_dataset("converged", data=np.array([[1.]], dtype=np.float64))
        for name in ("state_key", "timing", "history_channel_labels"):
            dataset = metadata.create_dataset(name, data=np.zeros((1, 1), dtype=np.uint32))
            dataset.attrs["MATLAB_class"] = np.bytes_(b"string")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(*, cycle: int, substep: int, source: str, file: str, sha: str,
        alias: bool, load: float, timing: str):
    return {
        "state_key": f"c{cycle:04d}_s{substep:02d}",
        "cycle": str(cycle),
        "substep": str(substep),
        "source_state_key": source,
        "payload_file": f"states/{file}",
        "payload_sha256": sha,
        "is_alias": "1" if alias else "0",
        "converged": "1",
        "imposed_displacement": repr(load),
        "timing": timing,
    }


def two_cycle_fixture(tmp_path: Path):
    c1_pre = tmp_path / "c0001_s00.mat"
    c1_peak = tmp_path / "c0001_s04.mat"
    c1_post = tmp_path / "c0001_s05.mat"
    c2_peak = tmp_path / "c0002_s04.mat"
    write_payload(c1_pre, cycle=1, substep=0, load=0.0)
    write_payload(c1_peak, cycle=1, substep=4, load=.125)
    write_payload(c1_post, cycle=1, substep=5, load=0.0)
    write_payload(c2_peak, cycle=2, substep=4, load=.125)
    rows = [
        row(cycle=1, substep=0, source="c0001_s00", file=c1_pre.name,
            sha=digest(c1_pre), alias=False, load=0.0, timing="pre_cycle_committed"),
        row(cycle=1, substep=4, source="c0001_s04", file=c1_peak.name,
            sha=digest(c1_peak), alias=False, load=.125, timing="post_history_commit"),
        row(cycle=1, substep=5, source="c0001_s05", file=c1_post.name,
            sha=digest(c1_post), alias=False, load=0.0, timing="post_history_commit"),
        row(cycle=2, substep=0, source="c0001_s05", file=c1_post.name,
            sha=digest(c1_post), alias=True, load=0.0, timing="pre_cycle_committed"),
        row(cycle=2, substep=4, source="c0002_s04", file=c2_peak.name,
            sha=digest(c2_peak), alias=False, load=.125, timing="post_history_commit"),
    ]
    return rows


def test_transition_rows_requires_exact_alias_identity(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    pairs = transition_rows(rows, [1, 2])
    assert pairs[1][2]["state_key"] == "c0001_s05"
    bad = [dict(value) for value in rows]
    bad[3]["payload_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="alias"):
        transition_rows(bad, [2])


def test_transition_rows_rejects_malformed_previous_s05(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    rows[2]["timing"] = "pre_cycle_committed"
    with pytest.raises(ValueError, match="previous s05"):
        transition_rows(rows, [2])


def test_preflight_hashes_all_payloads_before_decode(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    pairs = transition_rows(rows, [1, 2])
    inventory = preflight_payloads(tmp_path, pairs)
    assert len(inventory) == 4
    (tmp_path / "c0002_s04.mat").write_bytes(b"changed")
    with pytest.raises(ValueError, match="preflight hash"):
        preflight_payloads(tmp_path, pairs)


def test_preflight_rejects_payload_path_escape(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    rows[0]["payload_file"] = "../c0001_s00.mat"
    with pytest.raises(ValueError, match="payload path"):
        preflight_payloads(tmp_path, transition_rows(rows, [1]))


def test_preflight_rejects_payload_symlink(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    source = tmp_path / "c0001_s00.mat"
    target = tmp_path / "outside.mat"
    source.replace(target)
    os.symlink(target, source)
    rows[0]["payload_sha256"] = digest(target)
    with pytest.raises(ValueError, match="symlink"):
        preflight_payloads(tmp_path, transition_rows(rows, [1]))


@pytest.mark.parametrize("bad_cycles", [[1.9], [True], ["1"]])
def test_transition_rows_rejects_noninteger_cycle_requests_before_io(tmp_path: Path, bad_cycles):
    with pytest.raises(ValueError, match="exact integer"):
        transition_rows(two_cycle_fixture(tmp_path), bad_cycles)


def test_decoder_preserves_native_support_and_alias_equality(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    decoded, receipt = decode_stage0a_transitions(
        states_dir=tmp_path, rows=rows, cycles=[1, 2],
        expected_nodes=4, expected_elements=2,
    )
    assert len(decoded) == 2
    pre, peak = decoded[1]
    assert pre.d_node.shape == (4,)
    assert pre.u_node.shape == (4, 2)
    assert pre.history_gp.shape == (2, 4, 4)
    assert peak.strain_en_undgr_gp.shape == (2, 4)
    assert receipt["preflight_completed_before_decode"] is True
    assert receipt["numerical_s05_to_s00_alias_cycles"] == [2]


def test_decoder_rejects_non_float64_without_cast(tmp_path: Path):
    path = tmp_path / "bad.mat"
    write_payload(path, cycle=1, substep=4, load=.125, dtype=np.float32)
    item = row(cycle=1, substep=4, source="c0001_s04", file=path.name,
               sha=digest(path), alias=False, load=.125, timing="post_history_commit")
    with pytest.raises(ValueError, match="stored float64"):
        decode_payload(path, item, expected_nodes=4, expected_elements=2)


def test_decoder_rejects_logical_metadata_rounding(tmp_path: Path):
    path = tmp_path / "rounded.mat"
    write_payload(path, cycle=1, substep=4, load=.125)
    with h5py.File(path, "r+") as handle:
        handle["state_metadata/cycle"][0, 0] = 1.25
    item = row(cycle=1, substep=4, source="c0001_s04", file=path.name,
               sha=digest(path), alias=False, load=.125, timing="post_history_commit")
    with pytest.raises(ValueError, match="cycle"):
        decode_payload(path, item, expected_nodes=4, expected_elements=2)


def test_decoder_rejects_external_hdf5_link(tmp_path: Path):
    external = tmp_path / "external.h5"
    with h5py.File(external, "w") as handle:
        handle.create_dataset("d", data=np.zeros((1, 4), dtype=np.float64))
    path = tmp_path / "linked.mat"
    write_payload(path, cycle=1, substep=4, load=.125)
    with h5py.File(path, "r+") as handle:
        del handle["d_node"]
        handle["d_node"] = h5py.ExternalLink(external.name, "/d")
    item = row(cycle=1, substep=4, source="c0001_s04", file=path.name,
               sha=digest(path), alias=False, load=.125, timing="post_history_commit")
    with pytest.raises(ValueError, match="non-hard HDF5 link"):
        decode_payload(path, item, expected_nodes=4, expected_elements=2)


def test_decoder_reads_same_bytes_that_were_hashed(tmp_path: Path, monkeypatch):
    path = tmp_path / "stable.mat"
    write_payload(path, cycle=1, substep=4, load=.125)
    original_hash = digest(path)
    item = row(cycle=1, substep=4, source="c0001_s04", file=path.name,
               sha=original_hash, alias=False, load=.125, timing="post_history_commit")
    original_read = Path.read_bytes
    changed = False

    def read_then_replace(self):
        nonlocal changed
        data = original_read(self)
        if self == path and not changed:
            changed = True
            replacement = tmp_path / "replacement.mat"
            write_payload(replacement, cycle=1, substep=4, load=.125)
            with h5py.File(replacement, "r+") as handle:
                handle["d_node"][:] = .9
            replacement.replace(path)
        return data

    monkeypatch.setattr(Path, "read_bytes", read_then_replace)
    decoded = decode_payload(path, item, expected_nodes=4, expected_elements=2)
    np.testing.assert_allclose(decoded.d_node, np.linspace(0, .5, 4))
    assert decoded.payload_sha256 == original_hash

```

## FILE: tests/test_s09_stage0a_capability.py

```py
import csv
import hashlib
import sys
from dataclasses import replace
from pathlib import Path

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_stage0a_capability import (
    S09_E008_CONTEXT,
    _derive_native_weights,
    _qualify_decode_and_freeze,
    _qualify_full_trajectory,
)


FIELDNAMES = ["state_key", "cycle", "substep", "timing", "is_alias",
              "source_state_key", "payload_file", "payload_sha256",
              "nominal_load_factor", "imposed_displacement", "converged"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_qualified_fixture(tmp_path: Path):
    states = tmp_path / "states"; states.mkdir()
    static_dir = tmp_path / "static"; static_dir.mkdir()
    static = static_dir / "native_q4_mesh_dofs_quadrature.mat"
    static.write_bytes(b"synthetic-static")
    physical = {}
    rows = []
    loads = (0.0, .25, .5, .75, 1.0, 0.0)
    for cycle in range(1, 74):
        for substep, load in enumerate(loads):
            key = f"c{cycle:04d}_s{substep:02d}"
            alias = substep == 0 and cycle > 1
            source = f"c{cycle - 1:04d}_s05" if alias else key
            if source not in physical:
                path = states / f"{source}.mat"
                path.write_bytes(source.encode())
                physical[source] = (path.name, sha(path))
            filename, digest = physical[source]
            rows.append({
                "state_key": key, "cycle": str(cycle), "substep": str(substep),
                "timing": "pre_cycle_committed" if substep == 0 else "post_history_commit",
                "is_alias": "1" if alias else "0", "source_state_key": source,
                "payload_file": f"states/{filename}", "payload_sha256": digest,
                "nominal_load_factor": repr(load), "imposed_displacement": repr(load),
                "converged": "1",
            })
    index = tmp_path / "state_index.csv"
    with index.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader(); writer.writerows(rows)
    context = replace(S09_E008_CONTEXT, state_index_sha256=sha(index),
                      static_sha256=sha(static), expected_nodes=3,
                      expected_elements=2)
    return context, rows


def write_static(path: Path):
    g = 1 / np.sqrt(3)
    locations = ((g, g), (-g, g), (g, -g), (-g, -g))
    nxi, dndxi = [], []
    for xi, eta in locations:
        nxi.append([.25*(1-xi)*(1-eta), .25*(1+xi)*(1-eta),
                    .25*(1+xi)*(1+eta), .25*(1-xi)*(1+eta)])
        dndxi.append([
            [-.25*(1-eta), .25*(1-eta), .25*(1+eta), -.25*(1+eta)],
            [-.25*(1-xi), -.25*(1+xi), .25*(1+xi), .25*(1-xi)],
        ])
    xy = np.array([[0,0], [1,0], [1,1], [0,1], [2,0], [2,1]], dtype=np.float64)
    conn = np.array([[0,1,2,3], [1,4,5,2]], dtype=np.int64)
    nxi = np.asarray(nxi).T
    dndxi = np.asarray(dndxi).transpose(1, 2, 0)
    with h5py.File(path, "w") as handle:
        root = handle.create_group("stage0b_static")
        mesh = root.create_group("mesh")
        mesh.create_dataset("node_coordinates", data=xy.T)
        mesh.create_dataset("cells_0based", data=conn.T)
        quadrature = root.create_group("quadrature")
        quadrature.create_dataset("gauss_W", data=np.ones((1, 4), dtype=np.float64))
        quadrature.create_dataset("Nxi", data=nxi.T)
        quadrature.create_dataset("dNdxi", data=dndxi.transpose(2, 1, 0))
        geometry = root.create_group("geometry")
        geometry.create_dataset("t", data=np.array([[1.]], dtype=np.float64))


def write_state(path: Path, *, cycle: int, substep: int, magnitude: float,
                bad_float32: bool = False):
    dtype = np.float32 if bad_float32 else np.float64
    nodes, elements = 6, 2
    u = np.ones((2, nodes), dtype=dtype) * np.array([[.01], [.1]], dtype=dtype)
    d = np.full((1, nodes), magnitude, dtype=dtype)
    decoded_history = np.ones((elements, 4, 4), dtype=dtype) * magnitude
    history = decoded_history.transpose(2, 1, 0)
    with h5py.File(path, "w") as handle:
        handle.create_dataset("u_node", data=u)
        handle.create_dataset("d_node", data=d)
        handle.create_dataset("history_gp", data=history)
        handle.create_dataset("strain_en_undgr_gp", data=np.zeros((4, elements), dtype=dtype))
        handle.create_dataset("strain_en_degr_gp", data=np.zeros((4, elements), dtype=dtype))
        meta = handle.create_group("state_metadata")
        meta.create_dataset("cycle", data=np.array([[cycle]], dtype=np.float64))
        meta.create_dataset("substep", data=np.array([[substep]], dtype=np.float64))
        imposed = (0.0, .031249875, .062499875, .093749875, .124999875, 0.0)[substep]
        meta.create_dataset("imposed_displacement", data=np.array([[imposed]], dtype=np.float64))
        producer = meta.create_group("producer_metadata")
        producer.create_dataset("converged", data=np.array([[1.]], dtype=np.float64))
        for name in ("state_key", "timing", "history_channel_labels"):
            dataset = meta.create_dataset(name, data=np.zeros((1, 1), dtype=np.uint32))
            dataset.attrs["MATLAB_class"] = np.bytes_(b"string")


def make_decodable_fixture(tmp_path: Path, *, corrupt_key: str | None = None):
    states = tmp_path / "states"; states.mkdir()
    static_dir = tmp_path / "static"; static_dir.mkdir()
    static = static_dir / "native_q4_mesh_dofs_quadrature.mat"
    write_static(static)
    physical = {}
    rows = []
    loads = (0.0, .25, .5, .75, 1.0, 0.0)
    imposed = (0.0, .031249875, .062499875, .093749875, .124999875, 0.0)
    for cycle in range(1, 74):
        for substep, load in enumerate(loads):
            key = f"c{cycle:04d}_s{substep:02d}"
            alias = substep == 0 and cycle > 1
            source = f"c{cycle - 1:04d}_s05" if alias else key
            if source not in physical:
                source_cycle = int(source[1:5]); source_step = int(source[-2:])
                magnitude = (source_cycle - 1) / 360 if source_step == 4 else 0.0
                path = states / f"{source}.mat"
                write_state(path, cycle=source_cycle, substep=source_step,
                            magnitude=magnitude, bad_float32=source == corrupt_key)
                physical[source] = (path.name, sha(path))
            filename, digest = physical[source]
            rows.append({
                "state_key": key, "cycle": str(cycle), "substep": str(substep),
                "timing": "pre_cycle_committed" if substep == 0 else "post_history_commit",
                "is_alias": "1" if alias else "0", "source_state_key": source,
                "payload_file": f"states/{filename}", "payload_sha256": digest,
                "nominal_load_factor": repr(load), "imposed_displacement": repr(imposed[substep]),
                "converged": "1",
            })
    index = tmp_path / "state_index.csv"
    with index.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader(); writer.writerows(rows)
    context = replace(S09_E008_CONTEXT, state_index_sha256=sha(index),
                      static_sha256=sha(static), expected_nodes=6,
                      expected_elements=2)
    return context


def test_full_trajectory_qualification_binds_all_six_states_and_payloads(tmp_path: Path):
    context, _ = make_qualified_fixture(tmp_path)
    rows, receipt = _qualify_full_trajectory(run_root=tmp_path, context=context)
    assert len(rows) == 438
    assert len(receipt["unique_payload_inventory"]) == 366
    assert receipt["qualified_substeps"] == list(range(6))
    assert receipt["hdf5_open_count"] == 0


def test_full_trajectory_rejects_missing_s02_before_payload_decode(tmp_path: Path):
    context, rows = make_qualified_fixture(tmp_path)
    rows = [row for row in rows if row["state_key"] != "c0001_s02"]
    index = tmp_path / "state_index.csv"
    with index.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader(); writer.writerows(rows)
    context = replace(context, state_index_sha256=sha(index))
    with pytest.raises(ValueError, match="438 logical"):
        _qualify_full_trajectory(run_root=tmp_path, context=context)


def test_controlled_route_derives_weights_decodes_all_six_states_and_freezes(tmp_path: Path):
    context = make_decodable_fixture(tmp_path)
    result, hash_receipt, decode_receipt = _qualify_decode_and_freeze(
        run_root=tmp_path, context=context)
    assert result["verdict"] == "P1_CONTRACT_FROZEN"
    assert result["qualified_six_state_trajectory"] is True
    assert result["native_weight_receipt"]["source_static_sha256"] == context.static_sha256
    assert hash_receipt["unique_payload_count"] == 366
    assert decode_receipt["decoded_physical_payload_count"] == 366
    assert decode_receipt["decoded_logical_state_count"] == 438
    assert set(decode_receipt["decoded_substeps"]) == set(range(6))


def test_native_weights_are_derived_from_static_geometry_and_order(tmp_path: Path):
    context = make_decodable_fixture(tmp_path)
    nodal, gp, receipt = _derive_native_weights(
        tmp_path / "static" / context.static_filename, context)
    np.testing.assert_allclose(gp, np.full((2, 4), .25), rtol=0, atol=1e-15)
    np.testing.assert_allclose(nodal, [.25, .5, .5, .25, .25, .25],
                               rtol=0, atol=1e-15)
    assert receipt["nodal_weight_sha256"] == hashlib.sha256(
        np.ascontiguousarray(nodal).tobytes()).hexdigest()


def test_controlled_route_rejects_hash_valid_bad_intermediate_support(tmp_path: Path):
    context = make_decodable_fixture(tmp_path, corrupt_key="c0001_s02")
    with pytest.raises(ValueError, match="stored float64"):
        _qualify_decode_and_freeze(run_root=tmp_path, context=context)

```

## FILE: tests/test_s09_stage0a_p1_freeze.py

```py
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_multiobjective_update import merge_objective_gradients
from s09_stage0a_p1_freeze import freeze_p1_contract, half_ulp_float64, weighted_rms


def synthetic_fields():
    cycles = np.arange(1, 74, dtype=np.int64)
    nodes, elements = 5, 2
    nodal_weight = np.array([1, 2, 3, 2, 1], dtype=np.float64)
    gp_weight = np.ones((elements, 4), dtype=np.float64)
    d_pre = np.zeros((73, nodes), dtype=np.float64)
    # Lowest cycles in every band are near-stagnant; upper ranks have clear growth.
    magnitude = np.linspace(0, 0.2, 73, dtype=np.float64)
    d_peak = d_pre + magnitude[:, None]
    h_pre = np.zeros((73, elements, 4, 4), dtype=np.float64)
    h_peak = h_pre + magnitude[:, None, None, None] * np.array([1, 2, 1, -1], dtype=np.float64)
    u_peak = np.ones((73, nodes, 2), dtype=np.float64) * np.array([0.01, 0.1])
    return dict(cycles=cycles, d_pre=d_pre, d_peak=d_peak, history_pre=h_pre,
                history_peak=h_peak, u_peak=u_peak, nodal_weight=nodal_weight,
                gp_weight=gp_weight)


def test_half_ulp_is_positive_and_representable_at_zero():
    values = np.array([0.0, 1.0, -1.0, np.finfo(np.float64).tiny], dtype=np.float64)
    got = half_ulp_float64(values)
    assert got.dtype == np.float64
    assert np.all(got > 0)
    assert got[0] == np.nextafter(np.float64(0), np.float64(1))


def test_p1_freeze_is_deterministic_and_has_positive_normalisers():
    fields = synthetic_fields()
    left = freeze_p1_contract(**fields)
    right = freeze_p1_contract(**fields)
    assert left == right
    assert len(left["selected_cycles"]) == 16
    assert len(left["growth_cycles"]) >= 4
    assert len(left["near_stagnant_cycles"]) >= 4
    scales = [left["normalisers"]["damage_increment"],
              *left["normalisers"]["history_increment"],
              *left["normalisers"]["displacement"]]
    assert np.all(np.isfinite(scales)) and np.all(np.array(scales) > 0)
    assert left["scientific_execution_authorized"] is False


def test_p1_freeze_rejects_dtype_and_empty_stagnant_group():
    fields = synthetic_fields()
    bad = dict(fields); bad["d_pre"] = bad["d_pre"].astype(np.float32)
    with pytest.raises(ValueError, match="float64"):
        freeze_p1_contract(**bad)
    no_stagnation = dict(fields)
    no_stagnation["d_peak"] = np.ones_like(fields["d_peak"]) * 0.2
    with pytest.raises(ValueError, match="P1_NOT_READY"):
        freeze_p1_contract(**no_stagnation)


def test_weighted_rms_is_stable_for_tiny_nonzero_values():
    scalar = np.full((3, 4), 1e-200, dtype=np.float64)
    scalar_weight = np.array([1, 2, 3, 4], dtype=np.float64)
    assert weighted_rms(scalar, scalar_weight) == pytest.approx(1e-200)
    channels = np.stack([scalar, scalar * 2], axis=-1)
    np.testing.assert_allclose(weighted_rms(channels, scalar_weight), [1e-200, 2e-200])
    assert weighted_rms(np.zeros_like(scalar), scalar_weight) == 0


def test_p1_freeze_preserves_tiny_nonzero_displacement_rms():
    fields = synthetic_fields()
    fields["u_peak"][:] = 1e-200
    result = freeze_p1_contract(**fields)
    np.testing.assert_allclose(result["normalisers"]["displacement"], [1e-200, 1e-200])


def test_gradient_merge_projects_conflicts_and_clips_deterministically():
    gradients = [torch.tensor([2.0, 0.0]), torch.tensor([-1.0, 1.0]), torch.tensor([0.0, 3.0])]
    left, diagnostic_left = merge_objective_gradients(gradients, clip_norm=0.5)
    right, diagnostic_right = merge_objective_gradients(gradients, clip_norm=0.5)
    torch.testing.assert_close(left, right)
    assert diagnostic_left["conflict_projection_count"] > 0
    assert diagnostic_left["merged_norm_after_clip"] <= 0.5 + 1e-7
    assert diagnostic_left["order"] == diagnostic_right["order"]


def test_gradient_merge_handles_zero_and_rejects_nonfinite():
    merged, diagnostics = merge_objective_gradients([torch.zeros(2), torch.tensor([1.0, 0.0])])
    assert torch.isfinite(merged).all()
    assert diagnostics["zero_gradient_count"] == 1
    with pytest.raises(FloatingPointError):
        merge_objective_gradients([torch.tensor([float("nan"), 0.0])])

```

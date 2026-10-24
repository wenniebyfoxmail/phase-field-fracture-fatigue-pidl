# S04-E040 — exact-source review packet

**Snapshot:** `5aaa317ed55175e80acb581d922eb6a1a4cb6d49` on
`codex/pidl-u012-feasible-damage-20261024`, based on
`99339eedabe685a3d22912b700776e7ab881137d`.

**Scope:** one isolated, GPU-only Umax=0.12 PIDL numerical arm. No run has
started. This packet asks for a non-binding design/contract check of the
described exact snapshot; it is not a request to certify execution, FEM
agreement, or physical validity.

## Fixed intervention

The standard 8x400 AT1, seed-1, 15-substep RPROP continuation is retained,
including weights-only L2 `1e-5`, the original recovery checkpoint, fatigue
state timing, mesh, load sequence `[.25,.5,.75,1,0]` repeated three times,
RPROP hyperparameters, and the standard relative-loss stopping arithmetic.

The intervention removes irreversibility from the optimized loss by replacing
the raw damage map of one isolated `FieldComputation` instance. At each
physical-step start it freezes accepted `h`, `A`, `psi_prev`, and `q_ref`, where
`q_ref` is the raw third-head output from the same accepted network and input
path. For the current raw head `q`, it uses:

```text
t = 0.25 * clamp_min(q - q_ref, 0)
d = h + (1 - h) * t / (1 + t)
```

The committed helper uses `torch.clamp_min`, whose installed PyTorch 2.11
derivative at zero is one. Thus the selected derivative at `q=q_ref` is the
positive-side `0.25*(1-h)`, while it is zero for negative raw increments. `h`
and `q_ref` are detached cloned tensors; the helper rejects layout or finite
violations and stores the exact raw/damage tensors from the latest field forward.

The optimized scalar is constructed directly, rather than through
`compute_energy`:

```python
u, v, d = field.fieldCalculation(inp)
e_el, e_d = compute_elastic_damage_energy(
    inp, u, v, d, mat, pff, area, conn, f_fatigue=f_fixed
)
physical = e_el + e_d
loss = torch.log10(physical) + 1e-5 * sum(
    parameter.square().sum() for name, parameter in named if "weight" in name
)
```

`compute_elastic_damage_energy` mirrors only the elastic and damage branches of
the standard energy implementation; it has no `hist_alpha` input and never
calls `pffmodel.irrPenalty`. The standard `compute_energy(..., IRR)` is called
only under `torch.no_grad()` after the final field is cached, to log a detached
shadow `E_irr` diagnostic.

## Exact start, stopping, and state transaction

Before every inner solve and before every accepted record is committed, the
runner requires on the same device/dtype/mesh/order/field route:

```text
q(theta_accepted, inp) == q_ref        (torch.equal)
d(theta_accepted, h, q_ref) == h       (torch.equal)
```

The shared `fit.EarlyStopping` is used with CUDA float tensors, `F_prev=[0]`,
the original denominator `abs(F_prev)+np.finfo(float).eps`, patience 10 and
`min_delta=5e-7`. Each RPROP update occurs before the stopping call, and the
terminal iteration retains the previous-loss state exactly as the standard loop.
A cap, invalid value, or wall-time event is unaccepted.

The output transaction is ordered as follows:

```text
staged accepted state record -> reload audit -> staged evidence + manifest
-> staged state index -> publish record -> publish evidence -> publish index
-> prevalidate candidate pointer bundle -> atomic pointer publication -> readback validation
```

The accepted pointer is the only authority. Its index binds the state-record
SHA-256, evidence directory, artifact-manifest SHA-256, mesh and field-route
hashes, phase, and parent index. Each v2 non-root index also binds its parent
index SHA-256; the runner and analyzer recursively verify the whole chain to
the root before restoring, advancing, or reporting an accepted prefix. Both raw `q` and mapped `d` must be bitwise
equal after reload; numerical error tolerances are logged only as diagnostics.
The next step reloads the pointer-bound record, never an in-memory trial. A
candidate step receipt is deliberately `accepted: null` before pointer
publication; a non-authoritative `steps.json` may add post-pointer elapsed time.

The analysis tool recognizes this transaction: it uses
`accepted_state_pointer -> state_indices -> record hash -> manifest` to establish
the accepted prefix, treats only a pointer-bound `accepted:null` receipt as an
accepted phase, and can reconstruct a field/energy prefix if a crash occurs
before `steps.json`. It explicitly suppresses timing conclusions in that fallback.

## Fixed execution and claims

One fresh Taobo GPU directory only; no new seed, FEM calculation, replay of the
existing standard arm, retry, or additional arm. The runner permits at most
15 sequential steps, 10,000 RPROP updates and 240 seconds per step (the final
15 seconds are reserved within that 240), 3,300 seconds total, and an outer
3,500-second timeout. Comparison is only against the completed standard R001
over a common accepted prefix: strain, raw psi+, fatigue accumulation, physical
energy components, detached shadow `E_irr`, L2, update count and elapsed time.

Completion would establish only discrete forward feasibility and the specified
RPROP stop event. It would not establish field-space stationarity, global
optimality, FEM agreement, or physical validation.

## Local evidence for this snapshot

The following CPU checks passed against this exact committed code:

```text
python -m unittest discover -s tests -v
20 tests: OK
python -m py_compile source/feasible_damage.py \
  scripts/run_s04_e040_feasible_damage.py \
  scripts/analyze_s04_e040_feasible_damage.py
git diff --check
```

The tests cover map exact hold and selected derivative, bounds, h=1 behavior,
finite rejection, no `E_irr` helper path, elastic/damage component and gradient
equivalence, bitwise state reload, evidence-before-pointer publication, pointer
tamper rejection, deadline accounting, pointer-chain analysis including a replaced-ancestor rejection, missing
`steps.json` fallback, and manifest/mesh rejection before field comparison.

## Review question

Against this exact source/contract snapshot, identify only a concrete P0 or P1
contradiction that should block the one fixed run: (1) a broken feasibility or
selected-derivative invariant; (2) a plausible `E_irr` backward-graph leak;
(3) an atomic accepted-state/restart flaw; (4) a mismatch with standard RPROP
stopping or the frozen baseline; or (5) an analysis path that could report an
unaccepted step as accepted. Otherwise say whether the packet is adequate for
this bounded numerical run. Do not request an expanded experiment matrix or
infer an execution/physical conclusion.

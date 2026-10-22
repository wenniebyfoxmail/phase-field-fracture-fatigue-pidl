# Original P0 12-state node readout

This producer-only wrapper reuses the archived `ad749c8` builder, loader and
`fieldCalculation`. It evaluates the original float32 network and original
mapping once at each required physical state, including the exact load
`.11999988` at s4 and zero at s5. It reads no checkpoint histories, evaluates no
objective, takes no gradients or optimizer steps, and installs no common BC or
new damage clamp. The original builder internally creates and discards its
analytic initial-d array; this is not a recovered/committed history.

The result is an **original checkpoint + original mapping zero-update GPU
reread**, not certified bitwise identity to the training-time GPU field.
The six existing NCP CPU fields retain their failed source-objective comparison
labels. This node-only wrapper does not repeat or override that comparison.

## Inputs and output

Stage only `read_original_p0_nodes.py` and the case's
`analysis/original_baseline_inventory.json` in a fresh attributable producer
directory. The already resident archived NCP `contract.json` supplies original
absolute paths and SHA256 values. The wrapper requires its exact SHA
`a926dc82848512eb6f37eab5ba93b9a3d4995c66efe56d997a85c736351451ce`.

Minimum original dependencies are the 15 Python files listed in the wrapper's
`SOURCE_FILES`, `model_settings.txt`, `native_q4_original.inp`, and these 12
`trained_1NN_<step>.pt` files:

```text
step:   1  2  3  4  5   411  412  413  414  415   99  299
state: c1/s1..s5         c83/s1..s5               c20/s4 c60/s4
```

No checkpoint history, loss trace, FEM target, F1 predecessor, D3/D4 module or
current physics kernel is needed. Runtime packages are the existing producer
Python, NumPy, CUDA PyTorch, gmshparser and tensorboard (the last two are imported
by archived helpers). Source/settings/mesh and all twelve network SHA values are
checked before import/forward. The execution owner supplied the previously
unrecorded model 5/415 hashes in case logs/p0_missing_network_hashes_0814.json
before this readout; they are now bound in the inventory. All original inputs are
hashed again before completion.

Output is a fresh directory containing `attempt.json`, `mesh.npz`,
`c<cycle>_s<substep>.npz`, `progress.json`, and `complete.json` only after all
12 fields have been saved and read back exactly. Node NPZ keys are `u`, `v`, `d`
(float32 N-vectors); mesh keys are `node_coords` (float32 N×2) and `connectivity`
(integer E×4, zero based). Receipts bind physical state, actual float32 load,
model/source/input/output SHA and runtime/precision. An exception writes
`incomplete.json`; external termination may leave only attempt/progress.
Absence of `complete.json` is incomplete, never permission to silently retry.

## Producer command (prepared, not executed)

The execution owner first checks current GPU/process and disk availability and
selects a free device. Use a fresh `/mnt/data2` run root and output; do not reuse
the existing NCP output. The example 600-second hard deadline is per job and
does not establish an aggregate experiment budget. Choose the finite deadline
within the owner's actual authority. GNU timeout terminates this owned process
group; do not kill processes by shared username.

```sh
# Set P0_ROOT to a new /mnt/data2/drtao/wennie/<run_id> directory,
# P0_ARCHIVE to a new /mnt/data2/drtao/pidl_archives/<run_id> directory,
# and P0_GPU to the currently available GPU selected by the owner.
# Stage the two files in P0_ROOT/code and P0_ROOT/inputs first.
mkdir -p "$P0_ROOT/logs" "$P0_ROOT/tmp" "$P0_ROOT/cache" "$P0_ROOT/jit"
cd "$P0_ROOT"
nohup setsid timeout --signal=TERM --kill-after=30s 600s \
  env CUDA_VISIBLE_DEVICES="$P0_GPU" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  TMPDIR="$P0_ROOT/tmp" XDG_CACHE_HOME="$P0_ROOT/cache" \
  TORCH_EXTENSIONS_DIR="$P0_ROOT/jit" \
  /usr/bin/python3 -u "$P0_ROOT/code/read_original_p0_nodes.py" \
  --contract /mnt/data2/drtao/wennie/pf_s04e011_ncp_348be4b_20261017T2029Z/code/contract.json \
  --baseline-inventory "$P0_ROOT/inputs/original_baseline_inventory.json" \
  --inventory-sha256 f2af83d689c3dae67327acc545e59f15c69fb7252a97a02861a78cc427d23ffa \
  --output "$P0_ARCHIVE" --max-seconds 570 \
  > "$P0_ROOT/logs/readout.log" 2>&1 < /dev/null &
```

Record the launcher PID/PGID, GPU, cwd, command, log and exact wrapper SHA in
the owner's job record. Deploy this Mac-prepared file at its committed source
identity or recorded SHA; do not edit the original archived code. A receipt
with all 12 fields is the scientific data acquisition result. No additional
smoke or independent-review ladder is required by this wrapper.

Local preparation uses only one direct consistency check: parse the wrapper
without importing torch/project code, compare its fixed 12 state/load/model
bindings against the existing baseline inventory, and confirm the 15 dependency
names have original contract entries. No network forward or optimization is
run on Mac.

For scoring, retain P0–F0 and P0–F1 as distinct comparisons. Node/instantaneous
metrics require no fabricated history or f_solve. Full original residual or
fixed-f energy claims still require the actual original coefficient/history
timing; this readout deliberately supplies only fields.

# U0.115 PINN acquisition frozen run card

Run ID: `pf_u0115_acquire_39f8108fe96d406385e4011700cb47f9`.
Owner: this dialogue. User explicitly approved one GPU and 48h after code
review. This is S04-E016 synthetic acquisition, no Delta model training.

Source commit: `b6d56102daa7d45a6c196b72055010170e5f39fb` materialized from Mac
Git objects, not the dirty shared working files. Source bundle includes source/,
all tracked SENS_tensile Python modules and two tracked meshes. CODE_SHA256SUMS manifest SHA:
`2ad7b6a3a6001e4f9d4d6d4bddd3650352a04d43d8a1f7a4044cbfd302301f6c`.
Supervisor SHA:
`fccba7a4ccf204c28a55c3482932b15fe154b0d73b71a372279864972a682e7b`.
Independent review must bind both and the command stored in supervisor.

Settings: Umax .115; seed1; 8 hidden layers x400; init1; RPROP10000 max/step,
LBFGS0, relative tolerance5e-7; hard alpha1 zero-load recovery with histories
preserved; current_active fatigue history with fem_gp_tri3_g_mean; fem_gp_tri3
irreversibility penalty; nominal [.25,.5,.75,1,0]; 120 physical cycles maximum
plus recovery =601 steps. Native PINN fracture confirmation3 is preserved;
an earlier own-confirmed termination is recorded, never forced through or
replaced by the FEM event. Its paired eligibility is decided after retrieval.

Retain checkpoints/history every step; diagnostics at each s4/s5 and state0.
Mapping under this recovery offset: s4=5c-1, s5=5c. No FEM labels or event in
the solve. All existing settings are from the frozen runner, no core edits.

Producer: `gpu-taobo` / GPUServer8, `/usr/bin/python3`, torch2.7.0+cu126.
Single physical GPU via CUDA_VISIBLE_DEVICES; selection is live, not reserved
from an old snapshot. Detached supervisor starts a new process group, records
PID/cwd/command/GPU, stops that group at48h or archive50GiB, writes terminal
receipt, and never retries. ROOT plus ARCHIVE counts toward50GiB, including
log/cache/workspace. Timer covers child solve and exports. A budget
termination is partial/unqualified, not success.

Run root: `/mnt/data2/drtao/wennie/pf_u0115_acquire_39f8108fe96d406385e4011700cb47f9`.
Archive root: `/mnt/data2/drtao/pidl_archives/pf_u0115_acquire_39f8108fe96d406385e4011700cb47f9`.
Log/receipts at run root. TMPDIR/XDG_CACHE_HOME/TORCH_EXTENSIONS_DIR under
that root. Fresh archive required, exclusive LAUNCH_CONSUMED guard and exact
approved manifest verification precede training. No automatic old-checkpoint
resume is possible in the fresh archive.

Evidence: runtime/source review, run/terminal receipts, state/checkpoint
coverage, diagnostic inventory, actual PINN event semantics, retrieval proof
and comparison support. Acquisition success only enables G5 paired-data
qualification. It cannot establish FEM teacher validity or residual success.

Method dialogue is review-only. D0 has one owner here and waits for G5; D003
and old ridge runs are not repeated.

Review history: first candidate blocked on missing field_computation.py and
supervisor receipt/budget edges. Repaired package uses the hashes above;
6/6 mocked-child no-training tests PASS. Startup/Popen/TERM/cleanup paths
retain terminal evidence; elapsed budget uses monotonic time, final output
tally includes workspace and archive, code manifest rejects any unexpected
old archive/symlink (pycache excepted). Reserve30s polling/cleanup in48h.
The old FAIL is preserved and does
not authorize launch; final independent review of repaired hashes is required.

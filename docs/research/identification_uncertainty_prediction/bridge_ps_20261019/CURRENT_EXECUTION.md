# Current authorised BRIDGE-PS execution, 2026-10-19

Historical preparation documents remain retained. AUTHORITY_AMENDMENT_20261019.md supersedes their preparation-only boundary for this one run. This is HQ-delegated authority under verified direct user takeover/connection requests; no final-package human approval is claimed. See the sealed hq_authority_chain.json, independent_review_v3_authority.md and execution_manifest.json.

Exact executed runtime source 0faf16f8c7e9872956d3db89a3ced42505e4a9a4, package 7baafbd0f6da859022eae098509601fa280c6d87eb1845eb11ca6c33884bf295. Scientific/controller code and config remain byte-identical to d67f0ac6; only the authority contract and tests changed. 33 artificial tests pass in the established Miniconda environment, with Mac BLAS warnings retained; Homebrew Python lacked NumPy and its failed import is preserved locally.

Resource admission passed on GPUServer8: 64 CPUs, 1.16 initial load, 408.4 GB available memory, 653.9 GB free on /mnt/data2, fresh run root. Versions: Python3.10.12, NumPy1.24.4, Torch2.7.0, Matplotlib3.10.3. No GPU used. These are admission observations, not scientific validation. One detached controller started 2026-10-19T18:24:31Z, PID1314694; full command/paths in run_receipt_R003.json. The unchanged 1800s/1thread/8GiB/4GiB+4GiB and first-stop/no-retry limits apply. No separate scientific smoke occurred.

Actual evidence is stored in /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/IU-BRIDGE-PS-20261019-R003. The full 169,912,269-byte archive has been retrieved and hash verified. Independent saved-output and four-figure review found no numerical inconsistency. H_INNOV loss0.823602 improves B*8.11%, fixed C_RAW6.45%, donor5.53%;15/19 groups improve B*, with all three C30 groups adverse. A CSV-read-handle ResourceWarning escaped first-stop as an unraisable destructor exception. This is a real frozen stop-contract breach, not clean acceptance; original COMPLETE receipts and warning log remain untouched. Only explicitly caveated exploratory component evidence is retained. No repeat/repair-run occurred. See run_receipt_R003.json, evidence_receipt_R003.json and warning_contract_audit.json; the full README_analysis.md, independent review and Obsidian synchronization receipt are in the local evidence root.


## 2026-10-20 新批准后的科学复用决定

原B owner核对569cc865 BRIDGE-PS-v1.0与现有R003：同19组/1144起点/2288起点×H、同六臂与派生控制、同数据SHA、912+76 solves已经完成并取回。选择reuse，不重复模型工作或全量审阅，不新建RunID/授权/SSH。原ResourceWarning首停违约及探索证据边界保留，不因新批准改写旧接受状态。

保留H_INNOV候选：Δ=0.072689，H10/H40均正，逐组删一均正，优于对应donor；但C30/H40双通道失效和有限估计/选择敏感性阻止物理状态充分性或稳定局部演化主张。下一承重比较为已有SCB方案内加载匹配/独立裂长参考的自身vs替换历史干预，非rich/权重扫描；数据未确认不虚构运行准备。C27-A25四组单独冻结，未获本次重跑权限。

[科学判断、完整38单元表及下一完整验证](scientific_continuation_20261020/README.md) · [复用回执](scientific_continuation_20261020/reuse_receipt.json)。

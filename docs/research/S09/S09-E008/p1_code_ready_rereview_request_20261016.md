# S09-E008 P1 exact-commit Code Ready rereview request — 2026-10-16

第一行只输出 `CODE_READY_PASS` 或 `REVISE_AND_REREVIEW`。请用中文。

请复审 exact candidate commit
`b9f2a2ea999c43c637e2deb9ef407002bd487f97`。本包包含所有被导入的项目
源码、三个 CLI、五个实际测试文件、协议/config/status 和 round-1 原始回传；
全部内容均由 `git show <commit>:<path>` 生成。

请首先核对 round-1 F1--F8 是否闭合：

- F1：A002 的 `D=0.00016864539921617467` 与 damage RMS 分字段冻结，正式
  near-stagnant verdict 使用 `0.25 D`，分组非空和正 persistence baseline 在模型
  构造前核验，并输出实际阈值；
- F2：reviewed base-config SHA、重算 groups/scales/D/selection limit、packet config
  identity、外部传入 approved commit、tracked execution files、resolved parameter
  order 都 fail closed；width/lr/scales/groups/epsilon 等方法字段有漂移反例；
- F3：loader 校验 canonical identity/manifest bytes、bytes/count、固定 membership、
  dtype/shape/finiteness和状态语义，而非只相信 manifest 自述；
- F4：negative alpha、所有 projected/raw outputs/support weights、loss/metrics 的
  nonfinite 均 stop；`finite` 由检查得到；
- F5：run/archive 必须是两个批准根目录的 canonical direct child，拒绝 `..` 与
  symlink；resolver 显式绑定 approved hostname、physical GPU 和 environment，run
  前逐项比较；
- F6：loss、gradient、scheduled diagnostics 每个 successful update 增量 flush；
  failure receipt 写入 fresh approved archive root，包含 stage、commit、config、packet
  和 successful update count；日志区分 scaled training loss 与 physical-unit
  unscaled raw-increment MSE，并补 post-projection alignment/effective norm ratios；
- F7：objectives 必须是三项、实名且固定顺序；每步 parameter layout 对照 resolved
  config；missing/reordered objectives 都有拒绝测试；
- F8：本附件补齐 `s09_stage0a_packet.py`、`s09_stage0a_p1_freeze.py`、
  `s09_operator.py` 和四个先前遗漏的测试文件。

Exact candidate 的 focused synthetic/local no-training suite 为
`59 passed in 3.44s`；`ruff --select F`、`py_compile`、三个 CLI `--help` 和
`git diff --check` 均通过。没有 optimizer step、真实 packet export、SSH、GPU
preflight 或 producer execution。

若仍有 blocker，请给出文件/函数、触发条件、影响和最小修复。若 PASS，只允许进入
真实 packet export 与 read-only Taobo resolution/final execution-gate 准备；不自动
授权 optimizer training，也不构成科学结论。

## Exact-candidate attachment manifest

| File | Bytes | SHA256 |
|---|---:|---|
| `docs/research/S09/S09-E008/experiment.md` | 11150 | `40017ea1694cc99d343996378a537887961c2dd364b889ece793288f9e0f5f34` |
| `docs/research/S09/S09-E008/p1_memorisation_run_package_20261016.md` | 8552 | `c6902d5eafec612562c53ab5e4fae1c61de1a55f93c81339a76f4aedd478e7af` |
| `docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json` | 10051 | `0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b` |
| `docs/research/S09/S09-E008/p1_implementation_status_20261016.md` | 5716 | `314d1e3ddecc83cb85b2d11f8b05cfef842ae8713a25368338d69d3282241969` |
| `docs/research/S09/S09-E008/p1_code_ready_review_round1_20261016.md` | 15927 | `c982c81271832ccf60dd5f66afb3381f6f48f07e14ef5505a3f5949ba1b08e4c` |
| `source/s09_stage0a_capability.py` | 17862 | `a8c9dbc089f9146a68f2649d03d15e1c2606d3267cfbe99990d26622e0332525` |
| `source/s09_stage0a_packet.py` | 15015 | `02f1f742d3b69977d10db5ba46904864104ec7ce1dd93e7c5c660d39dae589e0` |
| `source/s09_stage0a_p1_freeze.py` | 7054 | `8502f52dad72d8310f514304f1837a1b493590b577f067cafc6bdcad8f358514` |
| `source/s09_stage0a_p1_packet.py` | 14539 | `0444923aaf32ef2969c66702fc201796e544cc0e39c9deac91c7112ea6f88105` |
| `source/s09_stage0a_p1_trainer.py` | 47744 | `a6425389d3a196e967afecf76314b100701a6e59d86be6adf2a24e929a2986d4` |
| `source/s09_stage0a_transition.py` | 12750 | `5d3040fcc05cbbbb354fba746b31b3f56a41167c8d6f8b5c9cdeb146567625ce` |
| `source/s09_multiobjective_update.py` | 3145 | `12e64d379db5e92aa2c8d28762d398e2d50f2233fc3342b9a39c51aeb425951f` |
| `source/s09_fem_physics.py` | 3903 | `795cbe360260505ac50bb613f04882fc710ae4fc6e3c18232ba957e6e45bce57` |
| `source/s09_q4_quadrature.py` | 2876 | `26b7009f542879f57cca4e2428af4183f6191db2095f8fd6089ba5620d091ecb` |
| `source/s09_equilibrium_operator.py` | 6880 | `7d2c22df1bc526a72993730aaf098859861d177a9d35922bfe5ca06e86f6c50a` |
| `source/s09_operator.py` | 4473 | `9f9064c5dbf8b096eefe8aada2ed18f09a8d7244324815dae65486cc8a2bba43` |
| `scripts/export_s09_stage0a_p1_packet.py` | 1026 | `115e7d729aa030cd1ce5f388d07717adb0f31a4ac99b13b501910b44cd332e32` |
| `scripts/resolve_s09_stage0a_p1_config.py` | 1631 | `f7011b1338d4531c335bd87e8920f061e096a842ec965f894708961024123ace` |
| `scripts/run_s09_stage0a_p1.py` | 899 | `9827d7afe5a09ef04d7d98189413ff4655ff709896c956f6dad09ea1901bb837` |
| `tests/test_s09_stage0a_p1_runner.py` | 14734 | `068ef1d46ceb9bc68977c4d9a8e8326edf667a8ae856d692528a3964af5b9e61` |
| `tests/test_s09_stage0a_capability.py` | 11646 | `26ec4810f3d9153b05963804462979dd6159ca7d747222260b218e31ea099217` |
| `tests/test_s09_stage0a_packet.py` | 10191 | `1a4f206d8eebc39b3911959951f06360afaa719801b434f24e5ad46756a1ceb2` |
| `tests/test_s09_stage0a_transition.py` | 7309 | `21333ba19db080f5111c090beddbe67501d701e879453d15b9a7a735e13b17f9` |
| `tests/test_s09_stage0a_p1_freeze.py` | 4892 | `b64493f7a9d75828e4f40e11b05024e15fb3da2b723d8a0948ed84f63357d382` |

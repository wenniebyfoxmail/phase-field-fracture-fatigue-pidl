# S09-E008 P1 exact-commit Code Ready review request — 2026-10-16

第一行只输出 `CODE_READY_PASS` 或 `REVISE_AND_REREVIEW`。请用中文。

请只审核 exact candidate commit
`f4f0d2eabbd3e6caa79105eddfe0b3bebf37cf2f`。这是实现级 Code Ready
审核，不要访问 producer、不要导出真实 packet、不要运行训练，也不要把审核
结论提升为科学有效性结论。

本次审核需要确认实现是否忠实于已经获得 `PACKAGE_READY_PASS` 的 P1 包：

1. packet exporter 是否重复完整 438-file/366-state qualification，并把 A002
   receipt、static、16-cycle selection、每个数组和 canonical manifest 的 identity
   fail closed 地绑定；loader 是否会拒绝 path/hash/schema/dtype/shape/value drift；
2. 配置解析是否按照固定顺序，在模型构造之前用同一 Q4/AMOR equilibrium
   实现计算并冻结正的 equilibrium normaliser，随后绑定 exact commit、packet
   hash、单 GPU 和 parameter order；无显式授权的 resolved config 是否仍不可执行；
3. 模型输入/输出是否仍是 Stage-0A mixed nodal/GP 的 `s00 -> s04 peak`
   映射，没有 future leakage、`s05` 或 rollout 含义；float64 scales、channel order、
   derived `f` 和 native supports 是否一致；
4. 三个目标是否分别求 full-vector autograd；unconnected parameter 是否按 frozen
   order 插入同形状零块；median norm equalisation、fixed cyclic immutable-reference
   projection、all-three mean、single global clip、single AdamW step 是否严格实现；
5. projected-output hard constraints 是否在所有 loss/metric 前检查；teacher
   prestate/state semantics 是否在模型构造前检查；raw proposal clipping/saturation
   是否只作为诊断而没有误计为 hard-constraint failure；
6. 每步日志是否覆盖 raw/scaled objectives、full gradient layout、unconnected names、
   norms、pairwise cosines、projection/zero counts 和 effective merged-direction binding；
7. initial/final metrics、1,000-update schedule、四个必要 verdict clauses、minimum
   outputs、fresh Taobo roots、no-CSD3、local/no-CUDA guards 与 failure receipt 是否闭合；
8. 49 个 local synthetic/no-training tests 是否足以支撑 Code Ready，是否存在会令
   首次 producer run 不可解释的遗漏。

若发现问题，请列出文件/函数、触发条件、影响和最小修复。只有没有必须在真实
packet export 或训练前修复的问题时才输出 `CODE_READY_PASS`。PASS 只允许进入真实
packet export 与 read-only Taobo resolution/final execution-gate 准备；它不自动授权
optimizer training。

## Exact-candidate manifest

所有附件内容均从上述 commit 用 `git show <commit>:<path>` 生成：

| File | Bytes | SHA256 |
|---|---:|---|
| `docs/research/S09/S09-E008/experiment.md` | 11150 | `40017ea1694cc99d343996378a537887961c2dd364b889ece793288f9e0f5f34` |
| `docs/research/S09/S09-E008/p1_memorisation_run_package_20261016.md` | 8062 | `f9fd25a65a0b0a5f3c4938c46d17d53d3585f087b5ade8a15c9ddb24aaa137b2` |
| `docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json` | 9751 | `b6bf3f35b114ab9eef986410657976c9cde09fc7cb9c0d5562b6f09b768c017b` |
| `docs/research/S09/S09-E008/p1_implementation_status_20261016.md` | 4174 | `40a88140faa60d66528db1044812836b8575b5b4cb98e9e124aad07805496d2a` |
| `source/s09_stage0a_capability.py` | 17862 | `a8c9dbc089f9146a68f2649d03d15e1c2606d3267cfbe99990d26622e0332525` |
| `source/s09_stage0a_p1_packet.py` | 12384 | `53bf71e255080e89b875b93c798705d03ee3f85d165405419a070fb9ef8a8769` |
| `source/s09_stage0a_p1_trainer.py` | 33831 | `5eb86ef3c7efa2afb1bb404910959178d132c159f20f544ed3ea243026cb6461` |
| `source/s09_stage0a_transition.py` | 12750 | `5d3040fcc05cbbbb354fba746b31b3f56a41167c8d6f8b5c9cdeb146567625ce` |
| `source/s09_multiobjective_update.py` | 2734 | `c6f08707a62c7e36b3948ef06d4f1020910b5fd90837f666d88ea895208c05ec` |
| `source/s09_fem_physics.py` | 3903 | `795cbe360260505ac50bb613f04882fc710ae4fc6e3c18232ba957e6e45bce57` |
| `source/s09_q4_quadrature.py` | 2876 | `26b7009f542879f57cca4e2428af4183f6191db2095f8fd6089ba5620d091ecb` |
| `source/s09_equilibrium_operator.py` | 6880 | `7d2c22df1bc526a72993730aaf098859861d177a9d35922bfe5ca06e86f6c50a` |
| `scripts/export_s09_stage0a_p1_packet.py` | 1026 | `115e7d729aa030cd1ce5f388d07717adb0f31a4ac99b13b501910b44cd332e32` |
| `scripts/resolve_s09_stage0a_p1_config.py` | 1314 | `a0f0127d049b9fe0ba4fbbe26a8d1d8790cc5f70445168e814ebe7355f3e616c` |
| `scripts/run_s09_stage0a_p1.py` | 899 | `9827d7afe5a09ef04d7d98189413ff4655ff709896c956f6dad09ea1901bb837` |
| `tests/test_s09_stage0a_p1_runner.py` | 9150 | `205b35312cb00a5e2fe4ae07262d4646518f085630583e871ba45ec657842d88` |

Local verification on the exact candidate: `49 passed in 3.21s`; `py_compile`,
three CLI help paths and `git diff --check` passed.  No optimizer step, real
packet export, SSH, GPU preflight or producer execution occurred.

# S09-E008 P1 package review round 2 request

请只复核第一轮 `REVISE_AND_REREVIEW` 的三项 finding 及 placeholder
resolution order。第一行只输出 `PACKAGE_READY_PASS` 或
`REVISE_AND_REREVIEW`。这是包级复审，不是 Code Ready；不要训练、不要
真实导出 packet、不要访问远程机器。

审核对象是 exact commit
`af25e1cfbbdff6f0b36cae35da22c6fea97ab93c`。本轮冻结的科学范围、16
cycles、width/rank、1,000 updates、三目标、判决阈值和 Taobo-only 边界均
未改变。

请逐项核对：

1. scale buffers 是否直接从配置值构造成 float64，前三个 history scales
   是否只用于 raw heads、全部四个是否用于 history data loss 和
   `L_judge`；
2. 每个 objective 是否使用同一个完整参数顺序，合法未连接参数零填充且
   记录，缺失 block 是否 fail closed；norm epsilon 与 squared-norm
   denominator 是否量纲一致，lower median、immutable cyclic projection、
   三方向平均和一次 clip 是否唯一；
3. 每项 hard constraint 是否已有比较谓词、容差、检查对象和检查时点，
   input f qualification、projected-output validity 与 raw proposal 诊断是否
   分开；
4. trainer commit、Code Ready、packet identity、GPU/environment、equilibrium
   normaliser、resolved config 和 final execution gate 的先后顺序是否闭合。

验证记录：

- `42 passed`：
  `tests/test_s09_stage0a_capability.py`,
  `tests/test_s09_stage0a_packet.py`,
  `tests/test_s09_stage0a_transition.py`,
  `tests/test_s09_stage0a_p1_freeze.py`；
- JSON parse 通过；
- `git diff --check` 通过；
- 未运行模型训练、optimiser step、FEM、远程命令或真实 packet export。

附件身份：

| File | SHA256 |
|---|---|
| `p1_memorisation_run_package_20261016.md` | `005a70d9f95e7d62af0e37eb230e62bf347c312fe81f8e02a9c4ee0daace62a1` |
| `p1_memorisation_run_config_20261016.json` | `b6bf3f35b114ab9eef986410657976c9cde09fc7cb9c0d5562b6f09b768c017b` |
| `p1_package_review_round1_20261016.md` | `0735ec2979c2150d0cf55ef1b6f71ff80e63a8e777d9f3ecb5028b8ec1ddccf5` |
| `source/s09_stage0a_transition.py` | `5d3040fcc05cbbbb354fba746b31b3f56a41167c8d6f8b5c9cdeb146567625ce` |
| `source/s09_multiobjective_update.py` | `c6f08707a62c7e36b3948ef06d4f1020910b5fd90837f666d88ea895208c05ec` |
| `tests/test_s09_stage0a_transition.py` | `21333ba19db080f5111c090beddbe67501d701e879453d15b9a7a735e13b17f9` |
| `tests/test_s09_stage0a_p1_freeze.py` | `b64493f7a9d75828e4f40e11b05024e15fb3da2b723d8a0948ed84f63357d382` |

若通过，允许的下一动作仍仅为：实现 exporter/trainer，运行 synthetic/local
no-training tests，并对候选 exact commit 进行独立 Code Ready 审核。通过
不等于训练许可，也不构成 accuracy、generalisation、rollout、FEM truth、
teacher validity 或 PINO benefit 结论。

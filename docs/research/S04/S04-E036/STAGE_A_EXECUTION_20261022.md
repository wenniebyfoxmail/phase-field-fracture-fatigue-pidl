# S04-E036 · Stage A 实际执行记录 · 2026-10-22

本记录追加实际执行证据，不改写旧 attempt、锁或失败。当前已确认 **prepare_05 准备成功；原生 disabled 对照及四组冻结场比较仍待完成，Stage A 尚未通过**。后续结果按新小节追加，不用新结果覆盖本节当时的边界。

## 当前分工与证据位置

本窗口只完成 Stage A。整体对照 owner 复用经核实的 A 结果，负责 Stage B、PIDL 对照及优化/表达归因；本窗口不重复运行 B 或训练。直接人方取消累计资源上限，但保留每 attempt 显式 authority、有限单任务防挂、最多 4 CPU 线程、单个原生求解串行、资源预检和进程归属保护；不改全局 PowerShell 策略。旧的 3 小时/零启动上限仍属于旧 attempt，不追溯修改。

本地 case：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/stage_a_20261021_2142`；下文 `case/` 均指此目录。生产目录为 `C:/Users/xw436/jobs/E036_A_20261021_2142`，producer 为 CITPC12。

- 当前分工：`case/analysis/continuation_03_division_authority.json`，SHA-256 `5a4faf49a36457409109e595b49097f811c6f6153545b5f1ac3f7c07da48fa40`。
- 准备结果汇总：[prepare_05_verified.json](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/stage_a_20261021_2142/analysis/prepare_05_verified.json)，SHA-256 `d7acf5ecde48773c7954b96334d8e7598d3ce135af744234184b02a690248ad1`。
- 先前启动及 prepare_03 失败：[控制器 v4 记录](STAGE_A_CONTROL_V4_20261022.md)。prepare_02 的具体 CIM 不匹配字段没有保存，仍不能确定；不能用后续 attempt 的 CIM 观测补成旧原因。

## prepare_04：manifest 解码失败，未进入 mock 或构建

prepare_04 使用新 Java FileChannel 哈希实现，实际通过 config、authority、manifest 的初始哈希检查，随后在 `e036_stage_a_prepare_driver.m:18` 的 `isstruct(m.files)` 断言停止。53 条文件记录值完整，但前 43 条字段顺序为 `path,sha256`，后 10 条为 `sha256,path`。该 attempt 的 MATLAB exit 为 1，supervisor 保留失败，`global_policy_unchanged=true`；没有 mock、MEX 构建或原生计算输出。

原始记录：`case/logs/inspect_prepare_04_first.json`，SHA-256 `9e7e3ae78d9b5f7f672ea0aa8aa1fb55947e8af2d3d77514c5583cd63223de2b`。失败及原字节保留。

prepare_05 只将这 53 条 manifest 记录统一为 `path,sha256` 键序，并附说明字段；逐项路径、SHA 值及数组顺序与 prepare_04 完全相同。新 config/authority 使用新 label、独占 build/output 路径及重新绑定的 SHA；MATLAB 源仍为同一 `code_04`。实际 prepare_05 日志打印 `manifest_json_types old04=cell new05=struct entries=53`，确认了本机两份 JSON 的解码差异。没有为通过断言而改变科学标准或跳过来源核验。

## prepare_05：软件检查和全新 MEX 构建成功

实际 MATLAB 为 `25.2.0.3177638 (R2025b) Update 5` / PCWIN64。driver 开始于 `2026-10-22T07:05:48.064Z`，结束于 `07:06:13.794Z`，记录 25.9748718 秒；watchdog 记录 35.0317666 秒。MATLAB exit 为 0，supervisor 为 `completed`，全局执行策略未改变。

| 已确认项目 | 实际结果及边界 |
|---|---|
| 哈希检查 | 15 项通过：已知字节、分块边界、短读及注入的 I/O 故障；不是实际 OS 故障或不可变快照证明 |
| 事务/mock 检查 | 28 项通过：17 原基础例与 11 附加例；接受后读回仅赋值一次，拒绝不赋值，仍是软件 fixture |
| 构建 | 10 份 `.f90` 源文件，8 个全新 object、8 个全新 module interface、10 份编译日志、2 份新 MEX；未复用旧 object/module |
| 构建来源 | `mex -f` 显式选择 Intel oneAPI 2025 / MSVC 2022 XML；保存原源/构建副本 SHA、命令、编译器配置、日志和二进制 SHA |
| 下载读回 | 38 份构建产物逐项 SHA 核对，包括 2 binary、8 object、8 module、10 source、10 log |
| 计算边界 | `native_calls=0`、`native_solves=0`；构建成功没有证明离散残差、U0 入场或真实求解通过 |

实际构建 XML SHA-256 为 `1915687ebc9645d140f3259d3c155d1af708b6f19274dee5f65a6672a04c08b5`。本次来源到新 MEX 的链由实际编译记录建立，不能由它反推旧安装 MEX 的来源。

| 保留产物 | SHA-256 |
|---|---|
| `prepare_05/prepare_result.json` | `0afb25e7441f80664408fee1daf32d080fdbce81d4be3ca18c90c7547d548e1d` |
| `build_pair_05/build_receipt.json` | `6fa67858dc9f93a1f8c0fc71954f3e6a94f9c9f3e0d7d4565e03037049d7af31` |
| `build_pair_05/completion.json` | `39d032b7d15b27effcb7eedd27a4ea2755e08cb525653a94cdfe59233ad3ac86` |
| `AMOR.mexw64` | `350dc6cdd7ae9e95bc787b3654e801b208151bafd115be587f40a7c191e0eca5` |
| `AT1_PENALTY_FATIGUE.mexw64` | `b58c67d91212bc7d6db23adee13eafe0be240af3bc00b98b5fe0a42243236d8e` |

前三项及全部 38 份下载产物位于 `case/raw_archive/continuation_03/preparation_05/`。两份 MEX 分别位于 build 的 `Sources/+phase_field/+mex/+fem/+assembly/equilibrium/` 与 `.../pf/`。运行日志为 `case/logs/inspect_prepare_05_second.json`，SHA-256 `ba01026d906cd04f2e5be4d570411d2ca80a7ebaa9d82798203c201d03506211`。

本次 config SHA 为 `bb5ea2b7d571a1e0a6d53ae3a5fb5f1fa1155375d5a57579aa2a48e605b6a099`，manifest SHA 为 `022c8efaea1734b49bf4d8ecc651eb398fbba496b594f8cdc523e07d2a8b53a4`，authority SHA 为 `234810af405777de35abfc7566f8ee1a0acec16c00d2c464ff28c864f60a8a52`。后续原生 job 复用并重新核对这一 build，不为取得整洁日志重复构建。

### 保留的 cleanup 警告与未部署修复

prepare_05 日志实际记录 `onCleanup` 析构时调用 `fopen('all')` 抛错并被 MATLAB 捕获为 warning；它发生在 fixture 的显式 `fclose(fid)==0` 已成功之后。15 项哈希检查继续完成，不能据此删去警告，或声称整个 cleanup 异常路径已经验证。先前静态审查未发现该 R2025b 运行兼容问题，实际日志修正了这一判断。

实际运行的 selftest SHA 是 `f3db9ce2adbb633d3e5a972861ba6d69b279c9380c60c4636739e6959c547fd4`。之后本地准备的 cleanup 源修复 SHA 是 `e558f5cc1363543b58a9358ac24e0d5386e1f73d3bfe980b4fdc216cdb892a78`；后者**未部署、未执行或测试，不属于本次构建/准备成功字节**。保留原 code_04、receipt 和日志，不重新运行准备或构建。

## 原生验证尚待完成；标准保持不变

准备成功仅满足软件检查与可追溯构建部分。后续必须保持以下原标准；完整方法见 [FEM 验证计划](FEM_VALIDATION_PLAN.md) 与 [实验记录](experiment.md)。旧计划中的累计时间建议由当前 authority 替代，物理条件和数值标准不变。

1. 绑定实际加载的 source/MEX/helper/CHOLMOD 路径、SHA、`which -all` 与当前构建 receipt；先检查有序 Q4 mesh、4 GP 顺序、权重、DOF/mask、完整物理状态键和前态来源。不得用文件编号代替状态键。
2. 共同材料为 E=1、nu=.3、Gc=.01、ell=.01、eta=0、AT1/Amor/plane strain、alpha_T=.5、p=2；不可逆罚系数 421875、恢复罚系数 13781.25；固定 251 个预裂纹节点 d=1，位移 BC 和五步载荷保持原值。
3. c1 输入仍是已保存的 E011 derived U0（source `67942510c38c420c9ebc343e88b781a018cd1c7b`，SHA `59a0f81368d0c46a698f94fdfcb32158e96361714d7547f00deed996d4a7c181`），不能称为 `862992a6` 的原始 native checkpoint。实际 U0 入场未通过时，disabled 对照 unavailable；不启动 recovery 或替换前态。
4. disabled 仍只作 c1s1 的 option absent 与 `enabled=false` 两臂，从同一 U0/缓存 tangent 起步，沿相同旧 native 路径；保留锁定内层设置及 outer≤1500。最终 u/d、四通道 history、停止信息、raw、last-inner history、tangent、保存 checkpoint 数组必须精确相等。第一臂失败不启动第二臂，失败不科学重试。
5. 冻结比较仍为预先指定 c1s4、c20s4、c60s4、c83s4，各自使用同圈 s3 前态；不优化场、不把存档末态自动认作合格参考。逐通道比较 native 与 float64 重装配的 Ru/Rd（完整、自由及 box 投影）、GP raw、active driver、A、f。标准固定为 `max_abs_difference <= 1e-10 + 1e-8*max_abs_reference`，不见结果后放宽。
6. 共同接受仍用 `nodal_box_kkt`：自由位移 residual 与损伤 box residual 的 joint tolerance `4e-4`，位移 `1e-6`；要求精确 `0<=d<=1`、`d>=d_old-1e-8`，active-bound tolerance `1e-10`，FEM history/commit identity `1e-10`。旧 history 固定，同一最终场 fresh 重装配后只提交一次；不隐式 clipping、不换用 soft-penalty 标准。PIDL float32 的 `2e-6` history 容差不用于此 float64 等价比较。
7. mock 接受/拒绝与读回通过仅证明 fixture 的事务行为；真实 native 保存/读回及最终场接受须由实际结果证明。未知进程先查证，不重复 spawn；非有限、来源/状态/BC/history 不符、资源冲突或数值失败保留原结果，不能继续推进未接受状态。

本节记录时 root 正准备 `disabled_05` 的隔离部署；尚无本记录核实的 disabled 或四组 frozen 比较结果。不得发布 Stage A 总通过、进入本窗口的 B/训练，或声称 timing 修复已减少 PIDL–FEM 场差距。

## 07:13 UTC serial producer wait

`disabled_05` package passed 495 source and 66 dependency hash checks, but resource admission found another owner’s MATLAB PID 34280 (`S04-E035-R020-20261022`). No launch request, watchdog or native output exists for disabled_05; this is an unconsumed label, not a failed numerical attempt. Do not stop or alter that process. Continue local package preparation and recheck availability before the same serialized Stage A work. Evidence: `analysis/native_resource_wait_01.json`, `logs/launch_disabled_05.json`.

## 07:20 UTC disabled_05：网格精度准备遗漏，未进入原生装配或求解

资源空闲后于 07:19:57 UTC 启动同一个尚未消耗的 disabled_05。07:20:20 UTC 终止，MATLAB exit=1；`e036_stage_a_context.m:48` 严格比较 U0 与导入网格时出现 `E036A:Mesh`。此位置在 DOF、System 构造和原生装配之前，两臂均未启动。watchdog/supervisor 终态、stdout/stderr 和 failure.json 完整保留；`Required arm receipts missing` 是未进入两臂的后续记录错误，根因是前述网格检查。全局策略未改变、仅自身 Job Object 关闭。

已保存 [disabled_05_failure.json](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/stage_a_20261021_2142/analysis/disabled_05_failure.json)。四个 frozen_05 包保持已暂存但未启动，避免重复触发同一入口错误。

独立只读数组检查证实：原始 INP 与 U0 的完整精度坐标和连接逐元素相等；实际导入器 `round(node,4)` 改变 172355 个坐标值、86543 个节点，最大差约 4.99999000558e-5。原 E011 的 `tools/prepare_s04_e011_fem_source.py:44–46` 明确删除该舍入。当前准备链遗漏了这一已有语义，不是容差应放宽、U0 应恢复或节点应重排的问题。后续仅准备新的精度保留导入 overlay，原 native、code_04、build_pair_05、失败05和历史结果不变；新入口须继续通过精确 mesh/DOF 检查。

## 07:38 UTC importer 修复后已进入真实原生求解

新 overlay_03 原样保留 overlay_02 的 solver/audit 文件，新增 importer 仅采用 E011 原准备变换：删除 elem/node 的 round4，nel 从连接列数取得。CRLF 保留；新 SHA `d8c6bc885f9f34759f9f1b0f9daa49ffb855e646efe9c5de0cc3ee1cd6470667`。native/code_04/build_pair_05 完全未改；严格 mesh/DOF/U0 判据未放宽。修复来源与代码 SHA 保存在 `case/analysis/mesh_import_repair_06.json`，独立诊断保存在 `case/analysis/disabled_05_independent_mesh_diagnosis.json`。

07:37:54 UTC，disabled_06 的 497 source/66 dependency 核对及空闲资源预检通过，按既有人方授权启动。07:38:24 UTC 实际 context_binding.mat 已写出、进入第一臂 native staggered/Newton，说明先前 mesh 检查与 U0 入场已通过；尚未得到双臂或 Stage A 结论。四个 frozen06 包使用同一修复与原构建，串行候场；旧 frozen05 保持未启动。

执行默认已遵循用户 2026-10-22 固定基准规则：只完成原有 disabled 和四个冻结状态，不追加全回归、历史重跑、smoke 或独立复审；已通过未受影响的 prepare05/build 直接复用。原执行卡治理修订本地 commit `f009d022`，未推送；活跃 fem helper 已同步，已结束 helper 未唤醒，共享 Roadmap 未改。

## 07:45 UTC 原生固定基准完成；比较启动修复

disabled_06 两臂完整 13 字段精确相等，保存检查点读回成功；native_driver_seconds=64.9351123，两个 native solve、两个 predictor solve、零 recovery。两臂 MAT 文件 SHA 不同并不代表数组不同（MAT metadata不同），实际逐字段精确比较已通过。33 份下载文件共 158844842 B 与远端 SHA 一致；见 `case/analysis/disabled_06_verified.json`。这是旧路径 disabled 兼容性，不是共同最终残差合格结论。

frozen_c1/c20/c60/c83_06 全部原生成功，均只作冻结装配、零求解；每个 21 份原始结果/日志已下载并核对 SHA。最后 c83 于07:45:15 UTC终止，各 supervisor 均 completed/global_policy_unchanged=true。

compare_c1_06 于 Python 创建前停止：PowerShell 5.1 的 `@(…|ConvertFrom-Json)` 将整个 14 项 argv 数组嵌成一个对象，故误报奇数项。只读实机诊断 old_count=1/new_count=14，移除外层 @() 后元素为 string；无 Python attempt 或数值结果。新 v5 控制器只修复该读取并版本化类名/标识，其 SHA 为 `e1ae0f4529440a93cbacdac9bcfdabeac01da65212d3d6884d973c53d235b905`。原 v4/失败06不改，其他 compare06 未消耗，改用新 compare07 label，复用全部成功 native06；07:50:57 UTC 已启动 compare_c1_07。详情见 `case/analysis/compare_06_launch_failure_and_repair.json`。

## 07:55 UTC Stage A 全部通过，交付复用

四个compare07均matched/exit0，4×29=116项固定比较全部通过；全部成功任务全局策略前后相等。185份原始文件共337439194 B下载核对SHA。详见 [完成与交接](STAGE_A_COMPLETED_20261022.md) 及case/analysis/stage_a_completed_20261022.json。

整体对照owner直接复用进入其负责的B/训练范围，本窗口不重复启动；存档FEM末态仍须原fresh接受标准。固定基准通过后不追加测试或复审。

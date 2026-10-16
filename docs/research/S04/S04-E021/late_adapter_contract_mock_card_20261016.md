# 四源只读适配器：合同与单次mock卡

2026-10-16 Europe/London。用户批准补齐适配层、元数据校验和授权交接，先mock，随后直接独立
静态代码审核；不批准真实数据读取、真实分析或拟合。本主对话唯一执行、记录和Obsidian写入方。
本记录不修改9984226方案、原核心算法、数据角色或已使用判据。适配层是工程准备，不是新实验结果。

## 输入合同及未闭合项

逻辑白名单固定为以下四条绝对路径，根目录统一是
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/`：

| 相对路径 | Git内可验证声明／用途 |
|---|---|
| runs/S04-E021-R001/percycle.csv | 六列和357周期覆盖由现有纯核心检查；只读权限、bytes／mtime须与保存清单一致 |
| replay_runs/S04-E021-REPLAY-R001/summary.json | s04_raw_replay.py声明的状态、四fold及3×2 stratum_mse；其余三个holdout晚期均值仅复制为保存背景 |
| control/S04-E021-REPLAY-R001_verification.json | 旧记录给出身份、行数、counts及晚期比值的含义，但无Git内producer／字段路径声明；真实selector UNBOUND |
| control/S04-E021-R001_saved_output_verification.json | verify_r001_outputs.py声明的身份和frozen_files；只核对唯一CSV条目，不访问清单中的其他文件 |

仅查看Git源码和既有研究记录，未读取、stat或间接从对话日志取回这四个真实源。
mock使用显式MOCK_SCHEMA_ONLY嵌套字段，不能冒充真实结构。`REAL_VERIFICATION_BINDING=None`，
真实入口在构造IO及源stat前拒绝；没有真实CLI、真实launcher或真实授权文件。
后续须先单独明确许可最小verification schema查看范围，再绑定、审查；本轮不做该查看。

## 最小实现及边界

- 精确四源白名单、规范路径一致性、regular file及每源≤1MiB；无扫描、哈希、旧模型／重放导入。
- O_RDONLY|O_NOFOLLOW；path与fd的dev／ino／mode／size／mtime_ns前后相符，异常仍关闭fd。
  CSV必须无写权限。该校验检测元数据漂移，不是内容认证，也不是OS级沙箱。
- strict JSON拒绝重复键／非有限常量；字段身份、保存比值、counts、三层均值与CSV覆盖校验。
  不新算R/G/Q、其他case归因或当前方案的describe分解。
- grant明确绑定代码、方案、尝试、输出、四源、预算、domain及禁拟合／禁确认；mock不授予真实访问。
  这些字段是机器联锁，不能自行证明人已批准。未来真实许可仍须来自用户并被独立核验。
- 父进程一次解析授权／输出绝对路径，子侧核对env及实际父PID，再交由显式callback读取授权。
  本轮callback纯内存；未实现实际授权文件reader或producer launcher。

## 唯一mock运行卡（执行前快照）

尝试 `S04-E021-LATE-ADAPTER-MOCK-R001`，新输出仅
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-adapter-mock-20261016-R001`。
固定worker／source列表的轻量配置复用已测监督器，仅为旧guard增加WORKER_NAME常量；
不重跑已消耗的LATE-ENG-R002或全部数值／绘图／资源mock。

上限60秒／512MiB聚合采样RSS／5MiB新增输出，含日志与回执；工作58秒留收尾，计量非OS硬限制。
只执行一次，失败或触限保留现场，不重试、扩预算或转机器。无GPU，CPU线程1。
候选源码提交后，将其完整SHA用于如下唯一命令的`CODE_SHA`参数；这是占位命令，不可原样执行：

```text
PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_late_adapter_guard.py --expected-commit CODE_SHA --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-adapter-mock-20261016-R001
```

工作目录为本专用工作树。预检源码干净、身份一致、新目录未消耗及无重复进程。
worker只生成内存四源，核对授权漂移先于IO、跨cwd绝对路径交接、metadata／身份／数值／schema拒绝、
fake-fd只读标志与关闭，以及未绑定真实入口先于IO拒绝。保护hook禁止真实科学源open；
它不是通用OS沙箱。mock不实际读取四源、不占满资源、不执行物理分析或创建授权文件。

结束后仅核对本次新目录的checks／log／receipt、进程终态、大小和权限，确认退出后只读冻结。
完成与否及真实资源以另存结果记录为准；本卡的准备时状态不回写为历史上已完成。

## 独立审核与后续

mock后绑定精确源码SHA直接交既有「多目标优化学习 FEM–PINN Delta」对话静态审核。
对方仅读Git源码和本次工程记录，不运行测试、读取真实源、实现、拟合或更新共享文档／Obsidian。
主对话核对意见；审核认可不等于真实输入绑定、真实授权或科学有效性。若有必改项先报告，
不自动追加第二mock。确认数据U0.1175／U0.125关闭，E017／NN／多目标训练暂缓。

# B003 — 字体初始化日志触发G01停止，资源包未完成

2026-10-18（Europe/London）。获批确切命令仅执行一次，实际exit70。
首个可见阻断为Matplotlib字体缓存WARNING；G01将其升级为进程非零退出。
未豁免日志、预热缓存、修改代码或重试，未启动独立验收、verifier或C/D。
本次不能判资源包完成；原65项人工兼容性和G01子进程结果保持各自原结论。

## 执行收据与预检

- Run：`S03-E019-D03-B003`；本机`Wennies-MacBook-Pro-14.local`。
- 工作目录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`。
- 输出：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B003`。
- source-commit：`87bc592d9c0828d0c698058702edca840e7e151d`。
- 运行前/后clean HEAD均为`657b95a1c9c07076739c6faaffffa3c22ac18d12`。
  启动前基线祖先成立、其后仅docs；外部前后七源码SHA与执行包逐项匹配。
- 执行包SHA256：`ba60afe401a66f3ffd07b4553618d2121c87479a1f24bdcf79795225d07ec758`。
- 启动前B003不存在（含软链检查），所有既有祖先为非软链目录；df约486GiB。
  未创建或预热缓存；本命令自行在新B003生成隔离缓存。
- CPU单线程、CUDA空、原容差及原60秒软预算口径保持；无新参数或后续命令。
- 前后观察时钟：UTC20:32:12–20:32:41，即BST21:32:12–21:32:41。
  是围绕运行和后查的窗口，不是精确进程起止或完整耗时。
- launch chunk2932c2返回session37711，等待1.002007667秒、无输出；
  只读poll chunk366052等待5.001587458秒、无输出；
  最终poll chunk7844a7等待0.050780667秒，exit70、无输出。
  三个等待段不相加冒充全进程wall。工具未返回PID，不猜测PID。

确切执行命令：

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/aa2024_q_recheck.py synthetic --source-commit 87bc592d9c0828d0c698058702edca840e7e151d --output /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B003
```

## 首停证据与组件结论

终端stdout/stderr合并流：三个chunk均空；外部最终exit70。
只读本次`runtime_guard_events.log`得到完整一行：

```text
G01 fatal logging phase=matplotlib_import thread=6116618240 Matplotlib is building the font cache; this may take a moment.
```

| 层级 | 本次证据 | 结论边界 |
|---|---|---|
| 执行身份/目录 | clean与七SHA不变；新B003专用 | 无源码或旧冻结产物改动 |
| 受保护停止 | 外部exit70且G01事件明确指向字体缓存日志 | 本次实际Matplotlib路径停止生效；不证明所有native/OS故障硬实时停止 |
| 数值阶段 | 文件名/大小显示certificate及report已写，事件在matplotlib_import | 源码控制流支持已到绘图导入；未解码、独立检验或接纳数值 |
| 完整资源包 | 无图、sidecar、execution_receipt、completion或failure_receipt | 未完成，不是资源检查成功或独立证书 |

源码控制流中analyze完成前检查1SVD/2QR，但本次没有最终收据，未打开report，
故分解次数只有控制流推断，不冒称独立核实的完整运行计数。没有为补齐证据
重算或读取数值内容。预算可见首阻断不是TimeoutError；缺最终预算完成记录，
不声称原60秒完成检查通过，也不把观察窗口当脚本计时。

与旧B002不同：同类日志这次没有被忽略后继续写成功标记。这个停止组件的
进展保留；整包仍未完成，不能由组件成功追认B002或证明真实DIC反演。
未生成结果图，故本次只用停止决策表，不显示或补画任何图。

## 原样保留的本次局部资产

只读顶层目录清单，未读取缓存内容或打开数值数组/报告：

```text
.cache/                     目录
.mplconfig/                 目录
certificate.npz             78468281 bytes
report.json                 116470 bytes
runtime_guard_events.log    123 bytes
```

没有PNG/PDF/sidecar或执行/失败/完成收据。G01的os._exit绕过finally/失败取证
是既定限制，缺failure_receipt不构成重试理由。保留上述局部资产，仅作本次
未完成运行取证，不覆盖、不清理、不用于后续科学结论；旧B002保持原样隔离。
运行后只读事件、目录元数据、Git与源码hash；未读report/certificate或任何
真实数组/stage15/新留出，未执行独立算术/图形验收或额外测试。

## 决策阶梯与下一步（未执行）

D1：受保护的合成资源路径是否完整完成？本次未完成，首阻断在字体初始化；
同时已得到本次真实日志路径的进程级停止证据。
D2：独立数值/图形验收仅在另批后考虑，本轮未进入。
当前转向R1：建议先准备字体初始化定位与数值/绘图解耦的最小方案，避免
为绘图环境问题重复SVD/QR；只在后续明确批准后检查依赖源或既有合成资产。
该方向不是当前代码更改、日志豁免、资源重跑、数值资产接纳或读取许可。
科学阈值与旧结果不变，不预设真实DIC根因；无新的执行授权自动继承。

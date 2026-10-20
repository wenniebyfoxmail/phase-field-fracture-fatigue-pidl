# MD03 D3 恢复执行待批卡 — R002（仅准备）

日期：2026-10-20（Europe/London）。当前 D3：区分散斑运动与新增／张开结构，
服务于图像观测到裂缝演化的研究。仅恢复部署，不改变研究问题或识别方法。
**本轮只授权准备与本地核查；没有授权 SSH、传输、解包或计算。**

## 请审核的一次性授权范围

批准本卡后，自动完成：一次准入 → 新目录及代码复制 → 一次完整输入传输 →
控制文件传输 → 校验与解包 → 单次 CPU 比较 → 有限只读状态检查与一次取回 →
可视化解释及 Obsidian 更新。机械检查满足后不逐步请批；任何失败按下述规则首停。
当前 approval_source 为 null；**没有 approved_decision.json，没有已启动的 R002**。

| 项目 | 拟议值／边界 |
|---|---|
| Producer | gpu-taobo → drtao@172.16.100.2:22，必须为 GPUServer8 |
| 拟议 RunID | MD03-D3-OPENING-20261020-R002；不是改名或续写 R001 |
| 新根目录 | /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002；必须不存在且不是悬空符号链接 |
| Runtime | /usr/bin/python3，Linux、Python≥3.9；不安装依赖或切解释器 |
| 科学源码 | 3991b5cdef8869fc652178af2787a1b082a70441；与 R001 完全相同 |
| 运行快照 | fb29771a2d972180c2d57b1fa6345dd4dbb684fe；两份原样科学文件的最小 Git 快照，不是新算法 |
| 科学预算 | 一次比较、一个逻辑 CPU／一条 OpenCV/BLAS 线程、0 GPU；科学 worker 硬墙限 **600 秒** |
| 内存／输出 | 任务及子进程各自虚拟地址上限 **2 GiB**；科学输出 **128 MiB**；不改系统限制 |
| 旧 R001 | 保留目录、残包、日志、首停记录及旧 rsync 进程；仅只读访问完整代码压缩包 |
| 结果目录 | 新根目录下 inputs/D3_controlled_opening_20261020/runs/MD03-D3-OPENING-20261020-R002 |
| 重试 | **0**：错误／超时／不匹配首停，无自动重连、补传、重启、改参数、换 host 或再造 RunID |

600 秒是继承的科学 worker 限额，不含串行准入、传输、解包和取回；辅助步骤时限
另列，不扩展科学预算。虚拟地址限不等同于已测得的 RSS 或实际运行耗时。

## 为什么这样恢复

上轮2026-10-20 **16:26:47 BST**只读快照：R001代码完整（44603字节、SHA匹配）；
输入仅2883584字节正确前缀（2.54%），完整输入与四控制文件缺失，未解包／计算。
两个指向 R001 的 rsync 进程仍在，不能把瞬间未写入当成永久停止。
**本轮未重新连接；上轮快照不保证当前网络／文件／进程状态不变。**
[原始证据与恢复依据](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/D3_controlled_opening_20261020/readonly_inventory_after_vpn_20261020/README_inventory.md)。

不在R001上续写、不操作其临时输入；完整重传113.5MB到新目录，复用44.6KB代码。
若源代码包重新核验失败，直接停止，不偷偷改为重新上传代码。

## 不变的科学对象

仅现有89、132、175三张图及批准缓存／掩膜，共9个既有文件。
仍是84固定位置 × 中央／两侧内部对照 × 5种既定位置变体 × 两个已曝光区间。
参数、坐标、保存的变换、质量阈值、缺失值处理及主比较均不变。
175仅作开发诊断，不按结果调阈值、选点或择图。

保留旧识别、半深度宽度定义和旧评分。内部对照不是独立无裂参考，可见性仍unknown；
不推定真实引伸计端点、物理开口或毫米裂宽。本次不计算新预测评分，不将旧5.81%
收益升格为独立预测验证。继承25个人工数组软件测试及原本地差异审核；
本卡不声称取得新的独立 agent 审核，也不要求重做未变的科学方案。

## 字节身份与控制文件

| 对象 | Bytes／SHA256 |
|---|---|
| 完整输入包 | 113514186／6ce79a5e1cd75615d2bf1b1712349409210244a878b4d5123e3059bd81279240 |
| 复用代码包 | 44603／f6fabf39e12355e87d4711b734217b0bbac3d491ea4c86ee653f68d4443e81e3 |
| 科学 Python | 27ad7b5c23f77f626bebd7e6659c26258bea6be327989bd9dbc21584db4cf8ed |
| 科学协议 | cbbb14a6e9e3916a4439a1a3d61ff4d7e3a3d75ba0fe83fedcfb7374b623a105 |
| 原测试文件 | 4f1599473329d278a058dfdd888d30c079e8629245bb744c0edfba50c5d64059 |
| R002合同 | f737cfd0673861b6ddf815e43be0cdcea1498bb0f767106006ff7c1d7548f057 |

[合同](recovery_20261020/remote_contract.json)与R001相比，**解析后仅archive根路径改变**。
JSON为未改科学runner的序列化格式（无末尾换行），避免其副本SHA漂移。
未重做prepare、重算变换或读图；新SHA仅由路径变化产生。

传入R002/control/的四文件：[remote_contract.json](recovery_20261020/remote_contract.json)、
[source_snapshot.json](recovery_20261020/source_snapshot.json)、
[run_cpu.sh](recovery_20261020/run_cpu.sh)、获本卡新批准后才创建的approved_decision.json。
[decision_template.json](recovery_20261020/decision_template.json)仅为null许可模板，
不能执行；R001旧许可不可复用。实际批准只填入可追溯的直接人方许可来源，
其他字段必须与新模板逐项一致。

本地执行资料目录拟定：
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/D3_controlled_opening_20261020/recovery_20261020_R002/
本轮只放准备核查记录；attempt/和collection/为将来执行的互斥标记，
不得删标记或复用失败记录来再启动。

## 获准后的顺序、时限与中止点

| 步骤 | 固定动作 | 时间限／停止点 |
|---|---|---|
| 1 准入 | 验主机／账户、新根不存在、R001代码SHA、runtime／工具、NumPy/OpenCV、Matplotlib模块、CPU/RAM/三挂载 | 60s；data2已挂载且余≥1GiB、MemAvailable≥4GiB、load1≤0.75×逻辑CPU数；不满足首停，不等资源／杀进程 |
| 2 新目录＋代码 | 原子创建R002，所有缓存／临时／日志在此；只读复制R001完整代码包，目的SHA再核验 | 60s；不覆盖旧根／已有文件，不读旧输入残包 |
| 3 完整输入 | 从本地原批准包传到R002，仅一次rsync | 总900s；无I/O120s停止；显式保留partial，不用append／inplace／delete／append-verify |
| 4 控制文件 | 传上述四文件，绑定R002新批准来源 | 总120s；未获许可／字段／合同不符，不进入后续 |
| 5 校验＋解包＋派发 | 全包SHA／输入大小及控制SHA；新输出不存在；输入tar限120s、代码tar限30s；Git快照干净且HEAD正确 | 总180s；失败不派发；原子launch.request防重复 |
| 6 单次科学比较 | nohup脱离SSH；实际Agg导入及源码／合同检查后原子launch.claim；taskset固定一CPU运行原run→worker | 原worker600s、2GiB虚拟地址、128MiB输出；只有一个worker，不重启 |
| 7 状态与取回 | 最多30次状态读取、间隔≥30s、总≤900s；核对start／worker／终态receipt；终态后列SHA并各取回结果／日志一次 | 单次读取≤60s，结果传输≤300s、日志≤120s，无I/O120s停止；逐件核验，无重复取回 |

每个计划SSH步骤仅一次连接尝试，ConnectTimeout=15s，禁ControlMaster复用，
ServerAliveInterval=10s/CountMax=2。**计划中的下一步骤／正常轮询不是失败重连**：
只要某次SSH／rsync失败，整个流程停止，不再发后续连接，也不改VPN。

派发PID不是科学启动／成功证据。以launch.claim/driver.pid、start_receipt.json、
worker_identity.json确认启动，以receipt.json确认终态。
派发应答丢失时记unknown，**不再派发，也不在本卡内重连查证**；之后须另获只读授权。
不得因“可能未启动”而重试。

若连接成功读到科学失败终态，允许本卡内只读取回已有证据，不再计算；
若传输／状态连接本身失败，则停止后续连接。没有终态／取回不完整如实记unknown／partial，
不能把派发成功或文件存在当成科学结果。

## 执行入口（本轮未运行）

获批后在上述本地资料目录创建独立批准文件，记录本次真实许可来源；
核对本卡部署脚本SHA，不回写或覆盖R001批准／首停记录。然后仅调用一次：

~~~bash
bash /Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp/docs/research/S03/S03-E049-MD03/recovery_20261020/execute_once.sh
~~~

[execute_once.sh](recovery_20261020/execute_once.sh)包含精确命令、局部日志、
独占attempt标记、总时限与首停；缺真实许可即在本地停止，不接触远端。
[first_admission.sh](recovery_20261020/first_admission.sh)是首次远端只读检查；
[stage_and_launch.sh](recovery_20261020/stage_and_launch.sh)在校验后解包派发；
[collect_once.py](recovery_20261020/collect_once.py)有限轮询、一次取回并逐件核验。

超时包装器只终止本次新创建的**本地子进程组**（SSH/rsync客户端），
不向远端PID发信号；远端残进程可能保留，按unknown／partial记录。
没有R001清理权限，不碰2730703/2730763及其父进程，不广域pkill；
若日后确需处理，先核验cmdline／elapsed／cwd／父连接，再取精确授权。

若用户要求中止，且R002科学输出目录已经存在，可仅在该目录创建STOP文件，
原worker逐测点检查后停止；目录未出现时不先造目录、不盲杀PID。此操作只在
实际要求中止时使用，仍受连接失败首停约束，不触及R001：

~~~bash
ssh -o BatchMode=yes -o ConnectTimeout=15 -o ConnectionAttempts=1 -o ControlMaster=no -o ControlPath=none -o ServerAliveInterval=10 -o ServerAliveCountMax=2 gpu-taobo 'test -d /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002/inputs/D3_controlled_opening_20261020/runs/MD03-D3-OPENING-20261020-R002 && touch /mnt/data2/drtao/wennie/MD03-D3-OPENING-20261020-R002/inputs/D3_controlled_opening_20261020/runs/MD03-D3-OPENING-20261020-R002/STOP'
~~~

### 部署脚本SHA256（不含将来才有的批准文件）

| 文件 | SHA256 |
|---|---|
| first_admission.sh | ce83f1c018189eb9c62258da36c3ff70056fc765d09b2067521495d8f645072d |
| run_cpu.sh | c9365dce790f42eeba7880bbcede0c46c81d74aafd6cd3438a970870a7c75a7b |
| stage_and_launch.sh | fefdf9ece2e794023cd7b22b53ab80981764c6aceccacfe14f28c4bccb4d5675 |
| source_snapshot.json | 1ed64881731b27baf56ffdc2269515fa4f2edf34de92c395dbe51cabf91a40e4 |
| decision_template.json | a5880ade82dabb1f61050d93700ac270802f6617d720b77d6e503367484538b3 |
| execute_once.sh | a3c9d1179fc5289197c122b8e04d20980436d1bf31e2e116fe6b3f36f3220deb |
| collect_once.py | 773d33383614e60ae1bbda245ba7c70f76185c43ea0fe27ddb4275783a100a5e |

## 交付及不包含的动作

成功取回后给两个区间逐例对比图、中央／内部对照开口证据、位置扰动包络、
覆盖率／缺失位置、原始记录与简明解释；图来自本次输出，不用旧图充数。
先视觉核查再解释，不把程序成功／数值可用等同真实开口。

本卡不含新图／附件、下载、作者邮件、训练、改识别／半深度／评分、参数搜索、
物理真值推定、共享系统改动、GPU占用查询／使用、CSD3／其他host、R001清理、
失败后的补传或再启动。作者回信不是本次计算依赖。

## 本轮实际完成的核查

[本地准备检查器](recovery_20261020/validate_preparation.py)只读元数据、字节哈希，
并调用bash -n／Python内存编译；没有运行部署入口、科学run／worker或renderer。
七组一致性检查通过：合同只改根目录、许可为空、科学／输入字节不变、launcher
仅改路径与合同SHA、脚本语法、脚本／卡片SHA和链接、一份输入／一次派发的保护。
[准备核查原始记录](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/D3_controlled_opening_20261020/recovery_20261020_R002/preparation_checks.json)。
这不是远端准入、独立agent复审、图像算法执行或新的科学结果。R002远端是否不存在、
当前依赖／资源／VPN、代码源是否仍完整，均留到本卡实际获批后的正常准入中核验。

**待用户审核。本卡及null模板不授权任何执行。**

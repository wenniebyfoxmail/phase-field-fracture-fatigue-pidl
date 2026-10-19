# S04-E011-UVH-C1-FN776-CARD-r2 — 新单次运行审批版

2026-10-19（英国时间日期）。当前仅获准备许可，未重连或执行。
本卡是全新Run；r1的SSH超时终态与所有旧证据保持不变。

| 绑定项 | 精确值 |
|---|---|
| CardID / 批准索引 | S04-E011-UVH-C1-FN776-CARD-r2 / S04-E011-FN776-r2-A1 |
| Dev | a674dc29fe915961267891bdf05410f74a78b14e |
| Producer根快照 | 04ff879176a5528988352c83a32a7617e1de9ef3 |
| 科学代码复用自 | f1ed1ed969b10637fa774b3a0cc29aa24b2b7f92；worker与square_root逐字节相同 |
| Bundle ref | refs/codex/fn776-gpu7-a674dc29fe91 |
| Bundle字节 / SHA256 | 197862 / 6c0f79d75170ddfa3211e2b0d9744bb33fe2c3de77f06452ab54e512fb1fb669 |
| 执行计划SHA256 | 0a3d336760bacb289c13dec418310cac352630eb75f9fe430c9a423aec3bc146 |
| 控制器blob | ccb9eddfd8385160254bf53e00d987d9d86818c7 |
| 新RunID | pf_s04e011_uvh_c1_fn776_r2_20261019 |
| 新root/code | /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r2_20261019/code |
| 新archive | /mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_fn776_r2_20261019 |
| GPU | Taobo物理GPU7，GPU-350d3f31-8bd6-4257-4d4c-21ad344eaa81，逻辑cuda:0 |

[精确执行计划](execution_plan_fn776_r2.json)逐条锁定argv/cwd/stdin字节与hash/
阶段次序和超时；[控制与部署修订](deployment_fn776_r2.md)说明全部实际变化。
卡的Git提交号在独立差异审核回执中记录，避免自引用。

## 科学方案、输入和判据不变

同c1s4、U=.11999988、MCS outer9固定FEM损伤、原模型/隐藏层/激活/UV提升、
388基底/776原z坐标、原网络z=0及同弹性能量E/E0。完整平方根分支Newton最多
16步、每步32个真实Armijo trial；无新表示、热启动、损伤/历史/隐藏更新、SVD
截断、ridge、loss改写、基线重评或备用求解器。

五输入完整路径、大小、SHA256和解码字段与r1一致，活动清单仅为
[inputs_fn776_r2.json](inputs_fn776_r2.json)：c1_peak.npz 15183163字节；
trained_1NN_4.pt 4510165；r2 head.npz 1204696（仅transform）；summary.json
2527；basis.json 11038；合计20911589字节。未来guard准入后整文件hash一次，
仅解码已列字段。本轮未stat/hash/read这些科学文件。

主判据仍为基底AD及实际网络力回投的原z梯度inf同时<=1e-8，实际/基底UV
差<=1e-9、能量差<=1e-10和冻结项不变；PBD相对能量增益>=1e-4且绝对增益
>10倍数值不确定性单独报告。数值驻点、能量见证、容量/物理/泛化结论分开。

## 预算、时钟与共享GPU

- 25424代理工作单位：曲率24832、控制64、trial512、最终16，各类不互借。
- guard900秒；600秒不再新增Newton/线搜索，840秒不再科学运算，890秒停
  自有worker并留10秒清理。输入IO/构造/QR/求解/序列化/图在同一guard钟内。
- worker树RSS<=8GiB、Torch reserved及自身NVML CUDA各<=8GiB；单GPU7。
- 总100MiB内预留1MiB控制诊断、1MiBproducer终止回执，producer正常产物
  采样阈值98MiB。源码检出与纯取回副本沿原统计口径；不额外增加产物预算。
- 运行显存空闲>=4GiB；准入>=12GiB、全卡利用率<=10%，host available>=16GiB，
  data2挂载且空闲>=5GiB。原采样间隔/已审服务身份规则不变；不保证硬峰值。
- 唯一新尝试；任一阶段失败/触限即终止，不重试、不自动重连、不换GPU、
  不加预算、不重置或购买额度。超时后只按已有字节记录未知状态。

仅允许空卡或既定两服务完整集合，首次模式固定三次采样及运行期：
PID2742304/start534715435（angle_main.py，494/1518MiB）；
PID2742215/start534715397（uvicorn det_main:service:18093，446/1470MiB）；
UID均[0,0,0,0]，cmdline/cgroup哈希逐项在清单内不变。这些是历史身份，
未作为今日观测；未知/子集/身份漂移/模式变化停止，不重加白、不停他人进程。

## 审批后的固定阶段

审批需涵盖：本卡/计划精确身份、只读SSH检查、新root部署、五文件读取、
唯一求解及报告取回。当前未执行这些阶段。先保存实际批准文本与运行意图；
用真实对话检查产生CASE/thread_duplicate_check.json，紧邻launch再次真实检查
生成launch_duplicate_check.json；各含run_id、checked_utc、no_duplicate=true及
实际核对范围，年龄<=60秒。不得使用样例或旧记录冒充新核对。

CASE为：
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_uvh_c1_fn776_r2_20261019/authorized_execution

唯一控制入口（Mac，不是科学求解入口）：

```bash
FN776_R2_CTRL='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/preparation/fn776_r2_20261019/package_a674dc29/materialized/code/tools/s04_e011_fn776/control_r2.py'
FN776_R2_PLAN='/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-c1-uv-energy-head-20261018/docs/research/S04/S04-E011/uv_head_c1_solver_d3_20261019/execution_plan_fn776_r2.json'
python3 -B "$FN776_R2_CTRL" --execute-approved --approval-ref S04-E011-UVH-C1-FN776-CARD-r2 --approval-index S04-E011-FN776-r2-A1 --plan "$FN776_R2_PLAN" --plan-sha256 0a3d336760bacb289c13dec418310cac352630eb75f9fe430c9a423aec3bc146 --step local_package
```

相同入口参数下，逐条显式调用以下step；不得用失败循环或自动重发：

| 顺序 / step | 阶段总上限 | 子命令与成功边界 |
|---|---:|---|
| local_package | 30秒 | 仅本地标准库verifier，精确Producer/闭包/逐blob/洁净检查 |
| preflight | **60秒单列** | 一次ssh -v/BatchMode/ConnectTimeout15/ConnectionAttempts1，只读主机、路径、同项ps、3样本GPU/身份及内存/挂载/旧终态检查 |
| upload | 60秒 | 一次SSH，新root独占mkdir，独占写唯一bundle；字节/hash一致 |
| deployment | 60秒 | 一次SSH，空Git init/fetch本bundle/detach精确Producer，标准库verifier |
| launch | 30秒 | 新鲜对话核对+远端同项ps；一次detached guard Popen，独占guard.log |
| monitor | 每次15秒，最多16次 | 每次上次成功后才可再观察，间隔>=60秒；无自动重连或重新启动 |
| manifest / archive | 各60秒 | 已确认终态后各一次自有报告清单/hash与tar副本传输 |
| verify_retrieval | 30秒 | 本地标准库路径/文件集合/大小/hash核验，不解码数组或补算 |

各阶段含4秒本地自有客户端TERM/KILL/reap清理预留，预检等待至56秒后停止，
不把清理变成额外预检。SSH -v与远端begin/end用于定位未来控制阶段；不修改
共享SSH master，不声称r1根因已确定。Guard仍有独立900秒预算。

launch计划内唯一科学guard向量为：

```text
/usr/bin/python3 -B tools/s04_e011_fn776/guard.py --execute-approved --approval-ref S04-E011-UVH-C1-FN776-CARD-r2 --expected-source 04ff879176a5528988352c83a32a7617e1de9ef3
```

cwd=/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r2_20261019/code，CUDA_VISIBLE_a674dc29fe915961267891bdf05410f74a78b14eICES固定上述UUID，Python优化关闭、线程数1；
stdin=/dev/null、stdout/stderr=/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r2_20261019/guard.log、start_new_session=True。Guard
自己排他创建attempt_claim并核验代码/重复/资源后，才读五文件和执行一次求解。
SSH失联不代表guard停止；控制端终止本尝试，不重发launch，也不自动重连。

## 审核与诚实边界

科学worker blob adb8c050b5330026cc120f47f14244ab040af028、square_root blob
0f485e08d39a55e4ee53f88d8e2652372a388a30与既有审核一致。新包无基础对象依赖，
51文件、649014选定字节、22本地模块闭包，空目录物化/fsck/逐blob检查通过。
本轮只做本地AST/text/Git检查，不运行控制入口、网络、资源mock或数值测试。
独立审查仅审控制记录/新身份/预算预留/包卡联锁的实际差异，沿用不变科学结论。

r1缺失的部分输出不可补造；其远端执行位置、连接根因仍未知。本修订增加未来
可观测性，未证明超时已修复，也不认证收敛、数值等价、900秒/8GiB可行或服务
性能。共享Obsidian与Roadmap由主S04更新，本对话不重复写。

批准可表述为：按S04-E011-UVH-C1-FN776-CARD-r2、批准索引S04-E011-FN776-r2-A1、
Dev a674dc29、Producer 04ff8791及本卡计划hash，在Taobo物理GPU7执行唯一一次新Run，
含卡内检查/部署/五文件读取/求解/报告取回；保持原预算和失败不重试规则。

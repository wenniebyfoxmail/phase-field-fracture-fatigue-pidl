# S04-E011-UVH-C1-FN776-CARD-r3 — 新单次运行审批版

2026-10-20（英国时间日期）。当前仅获准备许可；已完成一次独立hostname连接诊断，未执行FN776。
本卡是全新Run；r1终态不动，r2从未调用控制入口、未消耗尝试。本轮仅诊断连接并准备新卡。

| 绑定项 | 精确值 |
|---|---|
| CardID / 批准索引 | S04-E011-UVH-C1-FN776-CARD-r3 / S04-E011-FN776-r3-A1 |
| Dev | fd8408d53cbab3234d5066ba6706c25915a8a8d4 |
| Producer根快照 | 039c15015f64ca17b7013ad760cca8e6d19a5777 |
| 科学代码复用自 | f1ed1ed969b10637fa774b3a0cc29aa24b2b7f92；worker与square_root逐字节相同 |
| Bundle ref | refs/codex/fn776-gpu7-fd8408d53cba |
| Bundle字节 / SHA256 | 198010 / d602af37a657bbfba590b84ae49412883fc81bddb3d28e8ad0217f5f0ea91cdb |
| 执行计划SHA256 | fedb782866cfd226d1e7ee717e34f68769bbb7352f0fd5aceef6834387ec192d |
| 控制器blob | 29009ac938f61bb8c9091c0c37abff37c76ed5ec |
| 新RunID | pf_s04e011_uvh_c1_fn776_r3_20261020 |
| 新root/code | /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r3_20261020/code |
| 新archive | /mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_fn776_r3_20261020 |
| GPU | Taobo物理GPU7，GPU-350d3f31-8bd6-4257-4d4c-21ad344eaa81，逻辑cuda:0 |

[精确执行计划](execution_plan_fn776_r3.json)逐条锁定argv/cwd/stdin字节与hash/
阶段次序和超时；[控制与部署修订](deployment_fn776_r3.md)说明全部实际变化。
卡的Git提交号在独立差异审核回执中记录，避免自引用。

## 当前连接证据与最窄结论

2026-10-20 11:05:55至11:06:00 BST，一次独立探针只执行hostname：TCP0.225秒、
SSH banner0.484秒、公钥认证3.187秒，总4.356秒返回GPUServer8及exit0。
没有查GPU或科学数据。本卡连接固定为私有非复用会话：-T、ControlMaster=no、
ControlPath=none、ControlPersist=no、ClearAllForwardings=yes、PermitLocalCommand=no，
并保留BatchMode、ConnectTimeout15、ConnectionAttempts1。-v记录阶段，诊断-vvv
仅增加细节；不修改共享master或配置，不自动重连或切目标主机。

r1缺少原始阶段输出，原因仍无法归到连接/认证/复用/远端命令中的某一层；
旧自动复用仅是未证实解释。现在已验证上述私有连接可用，不等同未来资源准入。
控制工具复用control_r2.py等原文件名，实际RUN/Card/index和计划均绑定r3。

## 科学方案、输入和判据不变

同c1s4、U=.11999988、MCS outer9固定FEM损伤、原模型/隐藏层/激活/UV提升、
388基底/776原z坐标、原网络z=0及同弹性能量E/E0。完整平方根分支Newton最多
16步、每步32个真实Armijo trial；无新表示、热启动、损伤/历史/隐藏更新、SVD
截断、ridge、loss改写、基线重评或备用求解器。

五输入完整路径、大小、SHA256和解码字段与r1一致，活动清单仅为
[inputs_fn776_r3.json](inputs_fn776_r3.json)：c1_peak.npz 15183163字节；
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
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_uvh_c1_fn776_r3_20261020/authorized_execution

唯一控制入口（Mac，不是科学求解入口）：

```bash
FN776_R3_CTRL='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/preparation/fn776_r3_20261020/package_fd8408d5/materialized/code/tools/s04_e011_fn776/control_r2.py'
FN776_R3_PLAN='/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-c1-uv-energy-head-20261018/docs/research/S04/S04-E011/uv_head_c1_solver_d3_20261019/execution_plan_fn776_r3.json'
python3 -B "$FN776_R3_CTRL" --execute-approved --approval-ref S04-E011-UVH-C1-FN776-CARD-r3 --approval-index S04-E011-FN776-r3-A1 --plan "$FN776_R3_PLAN" --plan-sha256 fedb782866cfd226d1e7ee717e34f68769bbb7352f0fd5aceef6834387ec192d --step local_package
```

相同入口参数下，逐条显式调用以下step；不得用失败循环或自动重发：

| 顺序 / step | 阶段总上限 | 子命令与成功边界 |
|---|---:|---|
| local_package | 30秒 | 仅本地标准库verifier，精确Producer/闭包/逐blob/洁净检查 |
| preflight | **60秒单列** | 一次私有ssh -T -v/BatchMode/ConnectTimeout15/ConnectionAttempts1，只读主机、路径、同项ps、3样本GPU/身份及内存/挂载/旧终态检查 |
| upload | 60秒 | 一次SSH，新root独占mkdir，独占写唯一bundle；字节/hash一致 |
| deployment | 60秒 | 一次SSH，空Git init/fetch本bundle/detach精确Producer，标准库verifier |
| launch | 30秒 | 新鲜对话核对+远端同项ps；一次detached guard Popen，独占guard.log |
| monitor | 每次15秒，最多16次 | 每次上次成功后才可再观察，间隔>=60秒；无自动重连或重新启动 |
| manifest / archive | 各60秒 | 确认原guard及已知worker的PID/start_ticks身份已退出且有终态回执后，各一次自有报告清单/hash与tar副本传输 |
| verify_retrieval | 30秒 | 本地标准库路径/文件集合/大小/hash核验，不解码数组或补算 |

各阶段含4秒本地自有客户端TERM/KILL/reap清理预留，预检等待至56秒后停止，
不把清理变成额外预检。SSH -v与远端begin/end用于定位未来控制阶段；不修改
共享SSH master，不声称r1根因已确定。Guard仍有独立900秒预算。

launch计划内唯一科学guard向量为：

```text
/usr/bin/python3 -B tools/s04_e011_fn776/guard.py --execute-approved --approval-ref S04-E011-UVH-C1-FN776-CARD-r3 --expected-source 039c15015f64ca17b7013ad760cca8e6d19a5777
```

cwd=/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r3_20261020/code，CUDA_VISIBLE_DEVICES固定上述UUID，Python优化关闭、线程数1；
stdin=/dev/null、stdout/stderr=/mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r3_20261020/guard.log、start_new_session=True。Guard
自己排他创建attempt_claim并核验代码/重复/资源后，才读五文件和执行一次求解。
SSH失联不代表guard停止；控制端终止本尝试，不重发launch，也不自动重连。

## 审核与诚实边界

科学worker blob adb8c050b5330026cc120f47f14244ab040af028、square_root blob
0f485e08d39a55e4ee53f88d8e2652372a388a30与既有审核一致。新包无基础对象依赖，
51文件、650642选定字节、22本地模块闭包，空目录物化/fsck/逐blob检查通过。
本轮除上述一次hostname诊断外，只做本地AST/text/Git与差异审核；不运行控制入口、资源预检、mock或数值测试。
控制层补齐SIGTERM清理及guard/worker退出后报告冻结；SIGKILL/断电/无法写盘
不能保证回执落盘，状态缺失时仍须记未知，不能据此重发。
独立审查仅审控制记录/新身份/预算预留/包卡联锁的实际差异，沿用不变科学结论。

r1缺失输出不可补造，远端执行位置与根因仍未知。本轮仅证明当前私有SSH端到端
可用，不认证旧复用路径、未来资源、收敛、数值等价、900秒/8GiB可行或服务性能。共享Obsidian与Roadmap由主S04更新，本对话不重复写。

批准可表述为：按S04-E011-UVH-C1-FN776-CARD-r3、批准索引S04-E011-FN776-r3-A1、
Dev fd8408d5、Producer 039c1501及本卡计划hash，在Taobo物理GPU7执行唯一一次新Run，
含卡内检查/部署/五文件读取/求解/报告取回；保持原预算和失败不重试规则。

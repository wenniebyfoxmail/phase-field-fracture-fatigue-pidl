# D013 三态物理场预算完整输出头：Taobo CPU2 v2 最终执行审批

2026-10-20。**本卡只准备逐次审批，尚未发送文件、连接Taobo、创建真实批准文件或执行科学计算。** Mac v1原件继续保留并暂停；本版本仅修正部署层，原科学Code Ready沿用。部署和最终绑定审查收据见下。

## 本次申请批准的账号、对象与版本

|项目|本次唯一版本|
|---|---|
|负责人／准备机|Winnie／xw436；Mac用户wenxiaofang，开发与传输客户端|
|发送账号与对象|Mac现有SSH凭据 → **drtao@172.16.100.2**，主机必须为GPUServer8，Linux x86_64共享生产机|
|生产解释器／资源|**/usr/bin/python3**，CPython3.10至3.12；CPU计算库线程上限2、串行、0GPU，非空闲核预留|
|新生产根|`/mnt/data2/drtao/wennie/S04-E024-D013-CPU2-18d0e7cb-20261020-v2`；当前未远端检查或创建，审批后要求不存在|
|科学源码|`18d0e7cb1153dc969c1ee0c21c77ada1297b2d89`|
|科学树|`14f6ba5d4b0107e0655f711622ef51268222221e18666f65426bc11e42813c23`|
|唯一SCP文件|[D013_Taobo_CPU2_18d0e7cb_v2.tar](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_taobo_cpu2_package_20261020_v2/D013_Taobo_CPU2_18d0e7cb_v2.tar)，**272,097,280 bytes**，104个regular成员|
|SCP目标|`drtao@172.16.100.2:/mnt/data2/drtao/wennie/S04-E024-D013-CPU2-18d0e7cb-20261020-v2/payload.tar`|
|payload SHA256|`4e9f6f7ee2df07d62aac85c290398de261246a9971914d609a4c33c2d708427d`|
|action manifest SHA256|`b6463fdec674328c989ea123c5d4aeb6a41bb6776e38481b0bfeace9e3387806`|
|payload manifest SHA256|`7e9fcf09a97212cdfe883a71f421d085e740350ddc779b42d4ff2d0bbbf26675`|
|SSH正文／远端entry SHA256|`90fd6877578e9c1b992df140ef4708075f5df1e46622387ecdf7980ff5c70171`|
|Mac客户端SHA256|`7423e5e2dde20d32a5cda9135ebbaf4dd4f32bd245e42a55b1ad02deebe5b2c9`|
|原科学source tar SHA256|`4682bf96f178c4ca6dc9faf56a9f591cb687077e554240d77a997b818681d7b1`，压缩源原样复用，无代码漂移|

[完整动作清单](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_taobo_cpu2_package_20261020_v2/control/action_manifest.json) · [104成员及哈希](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_taobo_cpu2_package_20261020_v2/control/payload_manifest.json) · [88输入源／目标／bytes／SHA／用途](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_taobo_cpu2_package_20261020_v2/control/inputs_manifest.tsv) · [完整配对及输入JSON](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_taobo_cpu2_package_20261020_v2/control/inputs_manifest.json)。

88份输入合计**238,110,147 bytes**，全部从本地已回收原件随包携带，审批前只逐字节读文件，没有反序列化模型／场。D012三态历史头NPZ及原ARCHIVE_MANIFEST原样携带，不假定任何旧Taobo目录存在，不重求历史头。source解开1455文件、47,994,968 bytes，HEAD18d0e7cb与clean tree由静态字节核验绑定。

## 审批后的完整动作顺序

1. Mac客户端核对本卡action／控制文件／wire哈希、剩余累计时间和本地＋生产峰值存储；原子领取本次ACTION_ONCE，保存用户该次批准原话。无批准或false模板在任何SSH前拒绝。
2. **第一道SSH**：使用`-F /dev/null -o BatchMode=yes -o ConnectTimeout=15`，对上述账号执行`/usr/bin/python3 -c`，正文为本卡SHA绑定的remote_entry.py全字节、参数`--bootstrap-create`。同一SSH先交换monotonic锚点／截止时间，随后才做环境与资源检查；全部通过后仅领取新根／DISPATCH_ONCE，未数值求解。
3. **一次SCP**：上述唯一tar原样写入唯一新根的payload.tar。不给旧目录复制或补资产；上传失败／未知结果首停。
4. **第二道SSH**：同一账号／选项／相同完整正文，参数`--bootstrap-start`。沿用第一道锚点截止，校验wire／entry后单次脱离SSH启动新dispatcher `--run`；日志、PID、cmdline、cwd、时间、来源均落新根。
5. dispatcher核验104成员／88原始输入全部bytes及SHA、原source18d0e7cb／clean tree、Code Ready／检查收据及环境／预算；全通过后，仅删除下列**两个已核验的本次传输临时副本**：`/mnt/data2/drtao/wennie/S04-E024-D013-CPU2-18d0e7cb-20261020-v2/payload.tar`与`/mnt/data2/drtao/wennie/S04-E024-D013-CPU2-18d0e7cb-20261020-v2/package/science.tar.gz`。本地immutable wire、原输入、历史归档均保留。然后单次调用下述冻结科学入口并持续监督本次自有会话；不接管其他人的进程。

生产端科学调用（由客户端生成的收据必须已存在，不能手工绕过）：

```text
/usr/bin/python3 /mnt/data2/drtao/wennie/S04-E024-D013-CPU2-18d0e7cb-20261020-v2/code/SENS_tensile/run_s04_e024_field_budget.py
  --execute-scientific
  --project /mnt/data2/drtao/wennie/S04-E024-D013-CPU2-18d0e7cb-20261020-v2/project
  --out /mnt/data2/drtao/wennie/S04-E024-D013-CPU2-18d0e7cb-20261020-v2/project/local_archive/experiments/S04-E024/physical_field_budget_execution_20261020_v2
  --expected-commit 18d0e7cb1153dc969c1ee0c21c77ada1297b2d89
  --approval /mnt/data2/drtao/wennie/S04-E024-D013-CPU2-18d0e7cb-20261020-v2/science_approval.json
```

[**完整逐字argv／两次SSH全部正文**](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_taobo_cpu2_package_20261020_v2/proposed_exact_argv.json)，SHA256 `d221420461700a00a9f770ed12bd5c80a9ffb32c9df7ccd06ccfa0caa939018e`。此JSON展开完整正文，无shell占位符；仅供审阅，尚未执行。最终操作入口：

```text
/Users/wenxiaofang/miniconda3/bin/python3 /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_taobo_cpu2_package_20261020_v2/control/transfer_and_start.py
  --authorization /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_taobo_cpu2_package_20261020_v2/authorization.approved.json
```

该批准文件**当前不存在**；[现有模板](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/physical_field_budget_taobo_cpu2_package_20261020_v2/control/authorization.template.json)为false。只有明确批准本卡版本后，才根据本卡action生成绑定全部哈希、账号、根、预算、scope及该次用户原话的真实收据，不能把本卡自身或审查PASS当人方批准。

## 预检与机器现状

当前服务器可达性、Python及依赖和空闲资源均为**UNKNOWN／未探测**。要求：Linux x86_64／GPUServer8／drtao；/usr/bin/python3解析身份一致，CPython≥3.10、<3.13，禁`-O`。版本要求NumPy1.24.4、Torch2.7.0+cu126、SciPy1.14.1、Matplotlib3.9.2、psutil6.0.0、threadpoolctl3.5.0。Torch／NumPy来自2026-10-17回收记录，其余是所需版本，均不宣称今天已安装。元数据预检不导入真实Torch；真实模型／FEM准入只能在批准后各态数值worker发生。

/mnt/data2必须挂载；记录`df -h / /mnt/data2 /mnt/data3`、loadavg／affinity／内存／磁盘，affinity≥2、MemAvailable≥4GiB、data2 free≥2GiB。data3不存在只记录，不作为fallback；data2缺失即停。环境不符即停，不装包、换解释器、转Mac或换机。

所有缓存／临时文件／输出留新data2根，CUDA_VISIBLE_DEVICES为空，Torch／BLAS／OMP／threadpoolctl均2；不查询GPU、不继承旧GPU0共享许可。对自有进程做资源停止前，逐项核对cmdline、elapsed／create-time、cwd及本次fresh session，包含父进程退出后的存活worker；不以共享用户名归属进程。

## 三态身份与比较顺序

|状态|唯一原E023 joint10000／seed7 run|origin checkpoint SHA256|
|---|---|---|
|c20s4|S04-E023-head-rms-c4ceb5d-20261016-v1-R001-c20s4-localized-s7|`5431e187503a118b92a8649cac209da5e2b9c52643f73875535e208d92b9e5ae`|
|c60s4|S04-E023-head-rms-c4ceb5d-20261016-v1-R002-c60s4-localized-s7|`28c3182bc1721d4b692acbe6f622dff08a771f199b019d1985ccd66616ce9045`|
|c83s4|S04-E023-head-rms-c4ceb5d-20261016-v1-R003-c83s4-localized-s7|`07aa0a0edd28b15a8183961daa89aa2f8d8b703f6503c3a9b94231b05181c751`|

reference、producer D、坐标map、继承backbone、own E022、D012保存头的逐态SHA全部在上述完整配对JSON；禁止跨态拼接。c20早期、c60中期、c83转变期串行，每态依次strict η=.1、.3、1，以及中央η=.3旧七保护消融，共**12 profiles／9个主方案**。全部568维输出头；D／leak／features／backbone／BC／物理窗口／坐标map／damage／history／fatigue冻结；无NN更新和原checkpoint写入。

## 13项实际保护与累计预算中心

|量|实际不退化区域／定义|项数|
|---|---|---|
|UV误差|full／damage／background／窗口内background，全质量目标|4|
|工程应变误差|同四区域|4|
|瞬时弹性损伤驱动力误差|同四区域，`2(1-d)psi_plus`，不是历史驱动更新|4|
|弱平衡|实际原生质量对偶free-force范数平方|1|

主方案全部13项按真实量不退化；旧七仅诊断消融，不代替主方案。头先量化回原dtype，再经原rawencoder／Q4重建真实场；代理可行、线性预估或求解器success均不能替代真实接受。

累计预算Q是四个比值的最大值：全场UV变化／原E023 FEM UV误差，全场工程应变变化／原误差，瞬时driver变化／原误差，以及原生质量对偶free-force**向量变化**／原force范数。每项中心、尺度永久固定为**各自原E023终态**，重新线性化或已接受步后均不重置。原UV误差为零不求解；其他零尺度要求对应变化严格为零。没有2%参数球，也不把`.001`作为物理标准。

## 计算预算、空间与停止规则

|预算|原冻结限额及本次记账|
|---|---|
|CPU／GPU|计算库2线程，三态／profiles串行；0GPU；非两个空闲核预约|
|数值／重放汇总／绘图|1800／900／120秒|
|累计非训练／预检|300秒；原71.93754945798841秒不清零，v2本地包装／检查保守另记10秒，base **81.93754945798841秒**；本次传输／hash／环境／预检继续从余额扣|
|总上限|全部≤3120秒，不因换机器、失败或重建包增加|
|每进程RSS|3GiB，原legacy-loader 2GiB不放宽|
|归档|保留的旧／新本地D013包、检查与整个新生产根**合计1GiB**，不是每端各1GiB|

第一SSH在任何环境元数据前返回生产monotonic锚点；客户端收到ACK时的累计elapsed给出`anchor+(300-base-ACKelapsed)`，会保守提前截止。后续SSH／dispatcher使用**同一生产机绝对deadline**；科学交接仅在该deadline前预记5秒。全局同理使用3120秒deadline，不依赖两台机器UTC同步，也不将SSH客户端超时冒称远端取消。

本地冻结charge **444,931,767 bytes**（实有＋8MiB控制余量）；远端wire＋解包输入＋压缩source＋解开的source＋2MiB开销的保守峰值 **594,206,519 bytes**；合计 **1,039,138,286 < 1,073,741,824 bytes**。核验后删除上述两个远端临时副本，科学输出约余 **340,348,249 bytes**；不是预分配保证，实际整个根持续受同一上限监督。SCP前已在代码中要求local+wire及local+峰值均不超限。

每profile最多3次局部模型／SLSQP(maxiter200、ftol1e-10)，最多9个有序二分候选／模型，采用第一个真实合格候选；没有代理可行返回、solver exception或9个均拒绝则该profile止于最后已接受头。达到3次／数值收益停止沿用原规则。身份／SHA／非有限／物理映射／资源错误整体首停，余行保留incomplete，不记零收益。连接或传输失败／未知结果首停，不自动重发／重连／补资产／改代码／换机／换solver／扩预算／新RunID。

## 审查与交付边界

[原科学Code Ready](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-sampling-multiscale-20261012/docs/research/S04/S04-E024/physical_field_budget_code_ready_review.md)绑定18d0e7cb，原70合成／10语义检查沿用；未在本地重复导入真实Torch。[部署r4复审](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-sampling-multiscale-20261012/docs/research/S04/S04-E024/taobo_cpu2_v2/deployment_review_r4.md)通过，39项人工fixture加先前独立管道握手检查，首轮计时／存储及父退出worker清理问题与修订均保留。

[最终字节绑定审核](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-sampling-multiscale-20261012/docs/research/S04/S04-E024/taobo_cpu2_v2/deployment_final_binding_review.md) · [最终包收据](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-sampling-multiscale-20261012/docs/research/S04/S04-E024/physical_field_budget_taobo_cpu2_package_receipt.json)。本地准备未做真实NN／FEM前向、头部科学求解、训练或远端操作；科学执行与生产环境准入仍未发生。

批准后仅完整三态真实场与独立重放齐全才汇总：UV全场／损伤／背景／窗口内背景、应变、实际弱残差、瞬时driver及成本分开。保留跨平台原生LR／mass／D／rho严格检查例外，不能放宽检查凑通过。损伤演化／裂纹／疲劳应用仍需后续耦合与history验证，应用容差与背景接受预算仍未定义。

本次审批问题：**是否批准按本卡payload与action哈希，向上述Taobo账号原样传输，预检全部通过后单次启动D013三态离线校正，并允许只删除上述两份已核验的远端传输临时副本？**

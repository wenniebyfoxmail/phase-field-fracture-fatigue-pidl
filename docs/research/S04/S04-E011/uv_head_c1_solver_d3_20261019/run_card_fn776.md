# S04-E011-UVH-C1-FN776-CARD-r1 — 最终审批版

2026-10-19。当前仅获准准备；本卡尚未获得计算许可。批准对象是下列
完整源码包、单一新Run和预算，包含卡内只读SSH/重复与资源检查、源码
传输与部署、五个指定文件读取、唯一一次求解及报告取回。旧UVH/PC16
运行与失败记录保持原样；不维修、不重试旧r3，不重置或购买额度。

## 固定身份

| 项目 | 精确值 |
|---|---|
| CardID | S04-E011-UVH-C1-FN776-CARD-r1 |
| Dev源码 | f1ed1ed969b10637fa774b3a0cc29aa24b2b7f92 |
| Producer根快照 | e72d36e136600eee75644a50e530f6d7340fc7e8 |
| Bundle ref | refs/codex/fn776-gpu7-f1ed1ed969b1 |
| Bundle字节数 | 185682 |
| Bundle SHA256 | 39482f986345e8faeed64e30725b815731c3609279fab36c5f75241a538266f6 |
| 本地源码包 | /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/preparation/fn776_20261019/package_f1ed1ed9/code.bundle |
| RunID | pf_s04e011_uvh_c1_fn776_r1_20261019 |
| GPU | Taobo物理GPU7，GPU-350d3f31-8bd6-4257-4d4c-21ad344eaa81；worker逻辑cuda:0 |
| Root | /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r1_20261019 |
| Code/cwd | /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r1_20261019/code |
| 输出 | /mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_fn776_r1_20261019 |

本卡Git身份由后续审查回执记录，避免将自身提交号写入正文造成自引用。
源码包为无父提交、无基础对象依赖的完整bundle；空目录检出验证通过：
47个代码/文本文件、609923字节选定内容、完整fsck、干净工作区、逐文件
blob/大小/权限和19个可达本地Python文件的AST依赖闭包。包含此前涉及的
SENS_tensile/field_computation.py。核心source/SENS力学文件与既定源码逐blob
相同；8个保留科学函数AST相同。worker blob为
adb8c050b5330026cc120f47f14244ab040af028。

## 问题、输入与结果判据

按[协议](protocol_fn776.md)和[唯一输入清单](inputs_fn776.json)执行。
固定c1s4、U=.11999988、MCS outer9 FEM损伤、原模型/隐藏层/激活/UV提升、
同一弹性能量与E0。沿原388维基底、完整776维交错z，从原网络z=0开始。
不以旧r2/PC16拟合头热启动，不重新SVD/截断，不更新损伤/历史/隐藏层，
不增加材料残余刚度或损失正则，不重新求解或评价PBD基线。

| 唯一文件 | 字节数 | 允许解码 |
|---|---:|---|
| 既存c1_peak.npz | 15183163 | nodes,cells,freeu,u_fem,v_fem,d_fem |
| 既存trained_1NN_4.pt | 4510165 | weights_only state_dict |
| r2 head.npz | 1204696 | **仅transform** |
| r2 summary.json | 2527 | 清单列明的冻结原始/PBD/r2标量和判据字段 |
| r2 basis.json | 11038 | rank,columns,rcond,retained_condition,omitted_directions |

总计20911589字节；完整路径、SHA256和精确字段见输入清单，未来仅逐个
整文件核验一次并解码上述内容；不读head内拟合z/UV权重，不搜索额外数据。
本轮准备未读取、stat或hash这些科学文件。

完整平方根Newton：每GP三行能量平方根、4096GP分块、平衡TSQR对[A,e]
联合变换，保留全部776列，取T*p=-b并一致列缩放。原函数AD逐点能量/
梯度核对、每方向一次原函数AD-HVP核对；精确零迹采用压缩侧广义切线，
仅添加数学规定的零迹HVP校正。最多3次同根线性残差修正；原Newton
相对残差<=1e-3、后向误差<=1e-12、下降斜率<0。无ridge/jitter、秩截断、
平滑或备用求解器。最多16方向，每步最多32次真实Armijo F/g试探，
alpha=2^-j，j=0..31，c1=1e-4；仅显式接受后更新点并缓存已付费F/g。

主判据：原z坐标的基底AD梯度与实际网络力拉回梯度的无穷范数**同时
<=1e-8**；实际/基底UV差<=1e-9、原始能量差<=1e-10，冻结项不变。
另报PBD能量见证：相对增益>=1e-4且绝对增益>10倍数值不确定度。
能量改善不能代替驻点，驻点也不自动说明PBD增益或物理/泛化有效。

## 不可转移预算与停止规则

| 类别 | 单位上限 |
|---|---:|
| 完整构造/TSQR/诊断/求解/修正 | 16*1552 = 24832 |
| 控制 | 64；计划上界52 |
| 真实F/g试探 | 16*32 = 512 |
| 最终读出 | 16；计划3次 |
| **总计** | **25424** |

完整曲率槽1552=776*2为保守预登记工作代理，并非实测耗时等价。
各槽在工作前整槽扣费，失败也计入；HVP=2，E或E+g=1；不跨类借用。

- guard总钟900秒，包括其源码复核、输入IO、构造、求解、输出和图；
  600秒后不新增优化工作，840秒后不新增科学工作，890秒停子进程并留10秒清理。
- worker进程树RSS<=8GiB；Torch reserved及自身NVML CUDA占用各<=8GiB。
- Root bundle/log/回执及输出/tmp/cache合计<=100MiB，预留1MiB终止回执；
  已验证不可变Code检出不计入。任务缓存仅写data2。
- 运行显存空闲余量>=4GiB；准入显存空闲>=12GiB、全卡利用率<=10%，
  主机MemAvailable>=16GiB，data2已挂载且空闲>=5GiB。
- RSS/输出名义100ms采样；NVML名义1s采样、每命令2秒超时，属采样保护，
  不声称OS硬峰值保证。图和序列化在同一总钟内。
- 仅一次新尝试；部署/准入/身份/数值失败或触限均终止且不重试。600秒
  优化停止可在840秒前读出最后确认点；840秒停止后不再补科学读出。
  不改变源码/基底/阈值/随机种子/GPU，不扩大预算，不启动替代计算。

## 资源身份与重复核对

本轮未SSH，GPU7资源现况**未验证**。允许EMPTY或下列完整历史服务集合；
首次选择后对三次准入采样和运行期固定模式。只容许该集合加本worker；
未知进程、服务子集、PID/start/cmdline/cgroup/UID漂移、占用越限或模式改变
一律停止，不重新加白，不停其他进程。

| PID / start_ticks | 历史用途 | 基线 / 上限MiB |
|---|---|---:|
| 2742304 / 534715435 | python angle_main.py | 494 / 1518 |
| 2742215 / 534715397 | uvicorn det_main:service，18093 | 446 / 1470 |

两服务UID均[0,0,0,0]，精确cmdline/cgroup哈希在输入清单；这些是2026-10-18
历史身份，并非今日观测。审批后才只读查新样本，三次间隔1秒；过期即停止。
操作前核对当前其他对话，查疑似同项活动；部署前和紧邻guard启动前核对
Taobo Python worker、路径/claim/旧终止记录。未知状态先查证，SSH掉线不
代表任务停止，禁止盲发同一命令。不得给其他对话发消息或干预他人进程。

## 审批后唯一部署与启动

按[部署说明](deployment_fn776.md)，先完成只读SSH/重复/资源核对，再
创建全新Root；仅传上述bundle到Root/source.bundle，核验185682字节及
指定SHA256。任一冲突或失败停止，不修旧目录，不远程补对象。以下命令
是审批后的固定步骤，本轮未执行：

```bash
git init /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r1_20261019/code
git -C /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r1_20261019/code fetch /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r1_20261019/source.bundle refs/codex/fn776-gpu7-f1ed1ed969b1
git -C /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r1_20261019/code checkout --detach e72d36e136600eee75644a50e530f6d7340fc7e8
/usr/bin/python3 -B /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r1_20261019/code/tools/s04_e011_fn776/verify_code_package.py --code /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r1_20261019/code --expected-source e72d36e136600eee75644a50e530f6d7340fc7e8
```

再次核对无重复后，仅启动一次：

```bash
cd /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r1_20261019/code
nohup env PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=0 CUDA_VISIBLE_DEVICES=GPU-350d3f31-8bd6-4257-4d4c-21ad344eaa81 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /usr/bin/python3 -B tools/s04_e011_fn776/guard.py --execute-approved --approval-ref S04-E011-UVH-C1-FN776-CARD-r1 --expected-source e72d36e136600eee75644a50e530f6d7340fc7e8 > /mnt/data2/drtao/wennie/pf_s04e011_uvh_c1_fn776_r1_20261019/guard.log 2>&1 < /dev/null &
```

Guard先排他创建attempt_claim.json，此后准入失败亦消耗该卡；再次验证
源码包、干净状态与三次资源准入后，才允许读五个科学文件。worker独立
进程组；仅guard可终止其自有子进程组。守护PID/worker PID、主机、命令、
源码/卡/输入身份、资源样本、所有扣费及终止状态均落盘。

完成或失败后仅取回自有报告/部分记录，制作并校验传输哈希；不补算。
输出包括初始/末次未验证根、线性/AD控制、已接受/试探/原z梯度轨迹、
独立实际网络读出、summary、head、fields及decision.png+sidecar（若生成）。
失败保留缺失边界，不把静审、准入或部分轨迹视为科学成功。

## 审核边界与审批用语

当前完成的是标准库AST/text/Git检查与源码包空目录物化。没有导入数值
库、读取科学数组、执行夹具、矩阵构造、QR、梯度或GPU计算。独立静审修正了零迹附近分支变化的记录：仅按实际tau>0刚度分支计数，
负/零点数独立记录；不改变方向、能量或预算。最终精确复审回执另存；只评价该精确代码/契约，不证明收敛、900秒或8GiB可行。

可批准的范围为：“批准按S04-E011-UVH-C1-FN776-CARD-r1、Dev f1ed1ed9、
Producer e72d36e1，在Taobo物理GPU7执行唯一一次检验，含卡内SSH检查、
部署、五文件读取、求解及报告取回；遵守25424单位/900秒/8GiB RSS及CUDA/
100MiB预算、4GiB余量监测及失败不重试规则。”

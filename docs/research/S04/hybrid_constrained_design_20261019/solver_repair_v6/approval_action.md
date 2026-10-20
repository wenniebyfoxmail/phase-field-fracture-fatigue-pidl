# R3准确动作与预算（待自动审批要求的人方确认）

目的：按原比较方案，在相同物理接受精度下比较前态初猜、经典外推、神经damage初猜经完整约束校正的准确度与成本。v6只修复数值耦合方向/中间候选保护与机械线性求解成本，继承D13接受态字段与历史规则；不扩大材料、mesh、载荷族或网络/fit次数。

实现：`88c91249`，复审修正与固定R3 receiver：`dd0efd6e`。准确源以本目录`source_manifest.json`逐文件SHA为准。代码复审：`code_review.json`，142项人工回归全部通过，独立聚焦26项全部通过；真实大网格收敛、速度收益仍未检验。

## 需要确认的具体远端动作

账号/目标：沿用本机SSH认证，登录 `drtao@172.16.100.2`，脚本必须核验hostname为`GPUServer8`及drtao UID。GPU固定index5/UUID `GPU-5622bd47-1050-3003-246d-3cabe2b4791b`；不换机或换卡。

发送内容：只发送仓库 `tools/stage_hybrid_solver_v6.py` 标准库脚本（全文可直接查看），SHA256 `258794689908f2dc6bf759828be93a73a4f8e81c81f3c974d1dfb2e369896e5a`。输入科学数组不经网络上传；原输入与OSQP在同一服务器文件系统内，从 `/mnt/data2/drtao/wennie/pf_hybrid_complete_20261020_r2/{inputs,deps}` 复制到全新 `/mnt/data2/drtao/wennie/pf_hybrid_solver_v6_20261020_r3/{inputs,deps}`。8项输入文件（含原manifest）与OSQP经hash验证；总量≤160MiB/1024文件、OSQP≤32MiB；所有路径禁止symlink，不覆盖旧目录，不安装依赖。

准确远端命令（脚本作为stdin；本地45秒、单连接，无重试）：

```sh
ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 drtao@172.16.100.2 '/usr/bin/timeout --signal=TERM --kill-after=3s 30s /usr/bin/env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 /usr/bin/python3 -I -B -'
```

脚本先只读检查R2真实failed终态和归属PID、挂载/存储/RAM/16核/GPU空闲，再独占创建R3目录、复制和落盘stage receipt；不解码科学数组、不启动求解或训练。回传仅路径/hash/资源/成本JSON。任何失败或已有目录即停止，不能换ID重试。

stage通过后，按本次已授权任务自动把实际准备耗时加入同一累计账本，完成当前卡启用和准确包独立绑定复审；将本地经manifest固定的源文件及卡/复审JSON送往同一R3 `code/`（压缩≤2MiB/展开≤4MiB/≤256普通文件），由`tools/receive_hybrid_solver_v6.py`验证完整逐文件hash和卡/复审身份，仅一次调用现有`launch_hybrid_budgeted.py`；原signed R2卡/源/结果不改。receiver远端20秒+3秒kill，本地45秒，一次。最终源闭合或卡不一致即停止，不能无审查部署。

这一次运行只按原卡顺序执行：Agg环境准入、native replay、train_A/train_B/validation标签、一次fit、test_reference/test_classical/test_hybrid、原分析。所有三臂使用同一v6策略。归档目标 `/mnt/data2/drtao/pidl_archives/pf_hybrid_solver_v6_20261020_r3`；逐case记录elapsed、接受步数、失败/未完成迭代，不续跑或自动重试科学失败。

## 预算与不变规则

| 项目 | 本次限制 |
|---|---|
| 总研究墙钟资源 | 原136 hosth，不重置旧成本；16核，2176分配coreh |
| 已记录累计费用 | 809.844747秒（约13分30秒），含R2及其先前累计797.078552秒、已测本地dispatch/query；本地控制与生产日历重叠保守不扣除 |
| 当前可用host上限 | 135.775043h，后续stage/dispatch/清理继续扣除；这不是承诺所需运行时间 |
| 数值累计墙钟上限 | 原120h，已用497.477721秒，余119.861812h |
| GPU | 原12h，已用0；fit≤6h、hybrid≤6h；一次fit≤20,000 updates |
| 六条轨迹 | 每条120 cycles ×5子步 =600；本次新授权3600步；旧接受/失败尝试保留，不能声称累计只有3600 |
| phase上限 | train_A/B/validation/reference/classical各20h；hybrid6h；回放/分析共享4h |
| 单步工程保护 | 前瞻300秒，原120秒负结果保留；phase/累计预算不因300秒增大 |
| 内存与存储 | RAM64GiB、VRAM上限24GiB；primary128GiB+archive128GiB，空闲准入256GiB |
| 物理精度 | force1e-8、damage/KKT/投影1e-7、联合L2和4e-6、bounds1e-10、fatigue1e-8、QP1e-10；当前K LU pivot≥1e-14；全部不变 |
| 历史与停止 | accepted旧态不可变，trial仅从同一旧态构造，D13 f_solve/f_commit各自真实时刻；接受后CAS一次提交；首个科学失败即停 |

历史只读monitor三次的墙钟与部分控制CPU未单独测量，明确为缺测，不写零、不冒充完整实际账。科学worker终态/成本已取得；当前卡仍禁用，stage实际费用尚不存在，不填假数或追认未发生运行。最终绑定时保留此缺测说明及保守余量，预算不增加。准备/测试/代码审核成功不是FEM收敛或surrogate收益证明。

## 自动审批拦截的准确状态

两次工具调用均在CreateProcess前被拒绝，未执行SSH/stage/dispatch/求解。补充独立数据流核查后，第二次仍要求明确人方批准具体payload、目的地和私有输入同机复制的副作用。拒绝原文：

> 该动作会将本地求解器脚本发送至未被明确认定为可信的远端地址，并触发远端复制私有输入；用户授权了修复后重跑，但未明确批准这一具体 payload、目的地及数据复制副作用。

需要的人方确认只针对上述具体服务器/脚本/同机复制和后续已限定的一次重跑；随后代码/卡/成本等机械一致性核查与必要的既选通道复审由Agent继续完成，不逐项重复请示。

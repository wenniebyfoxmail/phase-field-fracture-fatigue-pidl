# PIDL c20四臂R1：记录代码首停；原生两臂可比较，冻结分支未运行

**目的：** 区分PIDL隐藏特征profile导数失配是否由源近似驻点或有限扰动跨弹性分支造成，以恢复PIDL复现FEM的路线。固定c20峰值s4/FEM damage、原PIDL源历史、B0 Smooth Boundary、原UV边界、实际Phi/T0、seed173方向与原h=1e-6。

**结果：** 计划四臂未完成。原生g=g0与原生零根重锚两臂的源/±量、Q/FD/difference完整保存；写第二臂汇总时因本次实现重复使用不可覆盖文件名而停止。冻结分支两臂没有运行。本轮不是成功的2×2比较，没有新PIDL优化端点或FEM求解。

## 失败原因和完成边界

源`fa9ce259de9c5a0938b68255ee1a98b647bb137b`，branch codex/hard5-q4-t3-2x2-20261005，启动前工作树干净。8项新增人工小矩阵/控制夹具及原独立渠道窄审通过；这仅是准备证据，真实运行仍发生记录缺陷。

`atomic_json`是独占不可覆盖记录器；我在循环中两次调用`atomic_json(archive/'partial_results.json',results)`，把可追加汇总的用法误套在不可覆盖接口。native_constant第一次成功，native_zero第二次抛FileExistsError。该错误发生在两臂FD/difference均保存之后、进入frozen分支之前；不是残差/FD门导致停机。第二臂标量汇总未写成，本地仅从已保存完整数组重新归约，不伪造producer成功终态。

Run `pf_s04e011_residual_branch_c20_r1_hq_20261021`；GPUServer8 GPU5 UUID GPU-5622bd47-1050-3003-246d-3cabe2b4791b，worker3901007/outer3900950/controller3900963/guard3900965、3901008。worker退出1、guard退出0，outer STOPPED_NO_RETRY，无外层异常。终态自有live=[]，网络/B0/物理状态unchanged=true，无OOM/非有限/遥测错误。没有自动重试、热换源、占其他卡或操作他人进程。

package SHA `f2038e42521864581634fc70160dcf0216f35522dc33e362d909e5c57d87bfc3`；authority SHA `99fe5a566a735089ccdc11e1ea6526c85163d5564ee57c724f6f98a98b495247`。远端run `/mnt/data2/drtao/wennie/pf_s04e011_residual_branch_c20_r1_hq_20261021`，archive `/mnt/data2/drtao/pidl_archives/pf_s04e011_residual_branch_c20_r1_hq_20261021`；完整命令/根目录/日志/PID见[执行收据](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/runs/pidl_residual_branch_r1_result_20261021/execution_receipt.json)。旧11-map与旧R1/R2失败均未修改。

## 已保存的原生两臂结果

所有数值来自本次原生弹性分支的固定chart场控制，不能称实际NN重新安装后的端点。原物理/head≤1e-10，内部头目标固定1e-13；原FDabs1e-10+rel1e-4不变。

| PIDL场控制（原生Q4弹性） | 保持g=g0 | 零根重锚g=0 |
|---|---:|---:|
| 源头物理梯度∞范数 | 3.36656e-11 | 1.46638e-15 |
| 源目标方程缺陷∞范数 | 2.71254e-16 | 1.46638e-15 |
| ‖Q−FD‖₂ | 0.009444733263 | 0.009444733342 |
| 原FD允许值 | 0.001305739625 | 0.001305739624 |
| 失配／允许值 | 7.233243966倍 | 7.233244033倍 |
| FD原门通过 | 否 | 否 |

源actualPhi投影旧3.3665696099e-11与fresh A0投影8.2728529973e-11仍按不同投影分列；新表constant的3.36656e-11是本次固定Phi实际算术读数，不是fresh A0。g−g0小与物理g小是两种检查，不能混为一个物理残差。

零根重锚源场相对constant只改变自由场L2=7.46362e-12；头zL2=2.79599e-14。两臂Q差1.79225e-7、FD差1.79378e-7，失配向量差1.81931e-9，约占共同失配的0.0000193%。两臂均观察到5个GP改变trace分支，源无exact-zero trace；最大导数失配节点同在(0.35099,−0.03927)。源AD primal与缓存根场身份检查通过；重锚J已包含B′z★，不是继续套旧z=0导数。

**可支持的结论：** 本方向、本h下，正确改变残差目标并重锚到更紧零根，没有明显消除原生导数失配。这削弱“只修源驻点条件就能解决主要失配”的解释；不能扩大为所有近似驻点／数值影响都已排除。

**不能支持的结论：** 没有冻结分支数据，尚不能判断Amor跨支贡献或做完整2×2交互归因；没有FEM/PIDL误差改善、网络容量或物理正确性结果。

![原生两臂FD检查，冻结分支未运行](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_residual_branch_c20_r1_hq_20261021/analysis/FD_four_arm.png)

![原生两臂导数失配场，冻结分支未运行](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_residual_branch_c20_r1_hq_20261021/analysis/FD_four_arm_fields.png)

图中NOT RUN明确表示缺失，不是零误差或失败臂。两图已检查共同色标、完整网格、标签和同名sidecar；CSV与[图QA](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/runs/pidl_residual_branch_r1_result_20261021/figure_QA.json)一并保留。图是位移导数误差，不是FEM/PIDL场差。

## 前向误差为什么仍未闭合

实际保存了源/两侧Jv、Cv、KJv、BᵀKJv、U、H/Cholesky、目标缺陷、物理force、实际Phi映射和GP标签；stored-H逆残差包络也已保存。完整`linear_solve_records.json`仅在正常末尾写入，本次首停前尚未写成，中间Newton各次线性求解的完整日志缺失，不能补造。已保存Q头响应/H/U允许做最后Q方程的小数组残差核对，但本报告没有新增求解。C项存在；矩阵/误差参数身份没有靠小梯度标量替代。

两侧储存矩阵的逆范数上界约0.8210–0.8217，逆残差包络<6e-9；自由B谱范数保守上界约7847。以已算直接头缺陷作局部线性校正，单侧场L2约1.5e-15–2.6e-15，但这不是完整原生非线性root误差证书。

加上投影归约的保守舍入估计、仍以已存nodal R为条件，FD方向的线性上界约6.0315，是原门约4619倍，远未达到门的十分之一。更何况native force算术误差和跨段强凸界没有完整证明。因此full_forward_bound_trusted=false；即使某个FD结果以后通过，也不能凭这些矩阵估计作唯一因果判断。实际Phi三大数组仅远端全核、未本地全量投影复算；不能称条件上界已被独立完整认证。

## 实际成本和取回

两机械批13.629840秒；worker科学阶段至失败27.862862秒，控制器最后elapsed约28.63秒。energy/field44＋K2=46/500，Qv2/4、hiddenJVP4/16、VJP0/16、dense15/50、factor15、triangularsolve38、rawfeature9、explicithead4、SVD0。source/±有限值缓存三次不等于总NN前向三次；AD源前向另计。

自有树峰RSS1691426816bytes，CUDAallocated11299426816／reserved12108955648bytes。远端475项／961590117bytes全部SHA/大小/覆盖核验；本地选126项／153465299bytes全核，压缩网络120058359bytes、取回119.421767秒、远端hash0.808022秒。远端export manifest SHA `8b7c6895d6a1ffe9c3899703ceaa5a268a13835a923ee54a51d4b95a88f1684e`，outer return SHA `7ea92a03c99667fcd215b7a773be10cca696c5f089000837be4eda39e9e3b420`。本地是部分镜像，三份大Phi仍在远端；远端全核不等于全量下载。[取回摘要](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/runs/pidl_residual_branch_r1_result_20261021/retrieval_summary.json)。

新增saved-only分析0.660734墙钟／0.659660CPU秒，无NN/AD/物理/切线/SVD/求解。初次人工测试模块路径错误及后续7/8项夹具结果保留，原独立8项与4个authority schema情形为准备验证；不将其计为科学成功。修复仅新增1项记录生命周期夹具，0.007秒。整包墙钟自23:08:58UTC计算，上限23:48:58UTC；整包CPU、精确kernel GPU时间、累计全部磁盘读取、货币成本未测，UNKNOWN不填零。旧112.405科学／1555.63整包和saved-only178.813墙钟／0.0277小脚本CPU及UNKNOWN全部保留，没有重置费用。

## 本地修复准备与下一决策

当前本地最小修复只把每臂标量写到唯一`<arm>_result.json`，完整汇总在全部完成后写一次；保留独占语义和重复同臂拒绝。新单项夹具用真实不可覆盖记录器验证两臂均可记录、重复同臂仍拒绝且首份不变。没有改变数学、阈值、材料、方向或预算。下一执行版还应将逐次线性求解记录同步持久化，避免异常前只留在内存；当前准备版未将此缺口伪装已解决。修复版仅本地准备，未新封执行包、上传、生成新RunID或再次运行；失败fa9ce259包保持不变。

下一项应先采用该记录修复，复用已保存原生结果和源缓存，决定怎样以最少真实工作补齐冻结分支与足够可信的前向控制；若必须重算源导数或完整四臂，准确工作量需重新绑定新前瞻授权，不能把旧剩余额度当自动重试许可。若完整控制显示仅冻结分支改善且误差界足够小，再转分支敏感度；若仍共同失配且界可信，转共有实现/有限步截断；界不足则继续未决，不能自动恢复3000秒优化。

冻结FEM基准与原PIDL基准不变：FEM E=0.0043205760、自由残差约3.78e-15；原PIDL E=0.0052684000、自由残差0.01348894、UV mass误差7.5487%、active加权relL2=6.120899／相关0.102518。本轮诊断根没有被接受为新PIDL基准，未导出的能量也没有事后补算。

原独立渠道对指定CSV／terminal／取回元数据及本地最小记录修复作了[一次有界结果核对](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/runs/pidl_residual_branch_r1_result_20261021/result_and_repair_review.json)：支持部分原生观察的有限结论，不把未运行frozen作负结果，不声称新包获得执行许可。该核对未新增数组/物理/测试或SSH，也未完整复核缺失的Newton中间日志。

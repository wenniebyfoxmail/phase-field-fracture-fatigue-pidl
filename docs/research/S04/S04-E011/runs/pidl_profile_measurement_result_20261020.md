# PIDL c20 profile导数机制比较：完成测量，原阈值仍未通过

**目的：** 为PIDL复现FEM场与平衡解决导数可信性问题。固定已收敛FEM c20峰值第4子步damage，保持源PIDL历史状态不变，并保留原UV边界、B0 Smooth Boundary、实际Phi复用及头梯度1e-10；本轮没有新的FEM求解或PIDL优化端点。

**结论：** 实际PIDL映射A与锚定chart场控制B的导数失配几乎相同。本状态、这一个方向的结果不支持“移动SVD保留族不一致”是主要来源；更指向两者共有的有限步长、分支、近似驻点或确定性数值影响，尚未分清。不能据此判断PIDL容量不足，也不能宣称预条件已改善FEM/PIDL误差。

## 本轮实际执行

HQ根据已核实的直接人方托管授权作新前瞻授权；它是一次600秒帽机制测量，不是重开旧R2或3000秒优化。源`049f1caec5b3d98a8228b6e57042cb4b775a1965`，分支`codex/hard5-q4-t3-2x2-20261005`，启动时工作树干净；package SHA `05399785deec707792f81d8e8222b85e0dbf56157fb2a0ce5e4d8b5a85cb1a93`，authority SHA `71e21d275e81281823cf07263e182f3ea93b67c55ba0fdc38185ab94fb9081a3`。旧5449d5a9/R1遥测失败、R2完整导数失败均保留，旧R2 manifest SHA核验未变。

Run `pf_s04e011_profile_measure_c20_r1_hq_20261020`，Taobo GPUServer8 GPU5 UUID `GPU-5622bd47-1050-3003-246d-3cabe2b4791b`。worker3831167，outer3831142/controller3831143/guardians3831144、3831168均已退出；终态自有live列表为空，未操作其他进程。完整命令、日志和根目录见[执行收据](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/runs/pidl_profile_measurement_result_20261020/execution_receipt.json)。

A做7次实际NN/profile映射：fresh-zero、±h、±h/2、重复±h，每次实际特征与SVD／Newton输出头。B复用同次A捕获的特征，在源变换T0锚定chart中做4次场级头求解，不安装成新NN。Qv只请求一次；h=1e-6，h/2=5e-7，seed173及原参数尺度不变。B是诊断控制，不能作为新的PIDL解。

## 结果：比较向量，而非只比较范数

Qv范数13.0573952482；原判据abs1e-10＋rel1e-4给出阈值约0.001305739625。头梯度阈值1e-10与这个导数阈值是两个不同检查。

| 映射／步长 | ‖Qv−FD‖₂ | 相当于原阈值 | 约占Qv范数 |
|---|---:|---:|---:|
| PIDL实际A，h | 0.0094440522 | 7.2327倍 | 0.0723% |
| chart控制B，h | 0.0094447604 | 7.2333倍 | 0.0723% |
| PIDL实际A，h/2 | 0.0067603667 | 5.1774倍 | 0.0518% |
| chart控制B，h/2 | 0.0067609636 | 5.1779倍 | 0.0518% |

四项均未通过原导数判据，未放宽阈值。这里的百分比是导数检查误差，不是FEM/PIDL解的差距。

A与B的FD向量差分别1.48494e-5／2.92786e-5，仅占A共同失配的0.1572%／0.4331%；失配向量余弦0.99999877／0.99999063。减半h使A失配下降28.42%，两点不足以证明某种收敛阶。fresh-zero场偏移为0，重复±h字段逐位一致，排除了本次读数中的源偏移及可见随机漂移。

A全部rank386，最大头梯度8.273e-11、实现误差5.555e-13；B最大头梯度2.740e-15，边界改变量0，A回滚／B源不变检查通过。B头更紧而共同失配仍在，但没有条件数前向误差界，不能凭此排除所有头闭合影响。

## 空间位置与分支

±h相对源状态共5个GP改变trace符号，±h/2共4个，A/B同侧标签逐位一致；源与各端点均无精确零trace。关联单元邻接20／16节点只占A失配平方和0.04148%／0.01494%。这不能排除分支变化经全局头求解传播的影响，尚不能说跨支解释了全部失配。

失配最高节点在(x,y)≈(0.35099,−0.03927)，两步长一致；前1%节点包含78.18%／85.86%的A失配平方和，|y|≤0.01带内为9.50%／6.75%。这些是位移导数失配位置，不是新的damage或active误差改善。

![A/B导数失配共同色标](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_profile_measure_c20_r1_hq_20261020/analysis/FD_mismatch_fields.png)

![trace改变位置](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_profile_measure_c20_r1_hq_20261020/analysis/trace_branch_changes.png)

橙色空心圈仅定位发生改变的微小单元，圈面积不代表物理影响范围。两图sidecar核验及目视检查完成，SHA见[图QA](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/runs/pidl_profile_measurement_result_20261020/figure_QA.json)。

## 成本、保存和独立核对

两批机械检查16.3878秒；真实测量112.4051秒，低于600秒科学帽。energy_force_field378/500、SVD7/7、native tangent1；head assembly22、factor21、triangular solves42；hidden JVP2为单次Qv公式内部调用，不是两个方向。无优化／历史提交／rollout。

全自有树峰值RSS3391201280 bytes，CUDA allocated10535014912、reserved11957960704 bytes；运行输出3818496984 bytes。无OOM／非有限值／遥测错误；不提供未测的核函数GPU时间或货币费用。完整任务含准备、复核、传输、分析与报告，绝对截止23:04:57UTC，未以科学墙钟冒充整包成本。

远端621项／3818496984 bytes全部逐SHA与大小核验；本地选择200项／39385104 bytes全部核验，压缩网络29014169 bytes，取回54.5736秒。**本地为部分镜像**，大Phi／checkpoint仍在远端；远端全覆盖验证不等于全量下载。详见[取回摘要](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/runs/pidl_profile_measurement_result_20261020/retrieval_summary.json)及[本地case](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_profile_measure_c20_r1_hq_20261020)。

分析仅使用已存向量、分支标签和冻结网格坐标；无新NN／AD／物理算子／SVD／求解。独立审查逐SHA/shape/dtype核35小数组，FD及difference逐位复现，跨平台范数差≤5.21e-18。独立审查初次BLAS余弦出现FP-status warning但数值有限，保留记录并用逐元素sum无警告核对，差≤6.66e-16；producer本身没有该warning。[独立审查](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/hard5-native-mesh-pidl-20260929/docs/research/S04/S04-E011/runs/pidl_profile_measurement_result_20261020/independent_array_risk_review.json)。

## 对原FEM/PIDL比较的影响及下一决策

冻结FEM仍E=0.0043205760、自由残差约3.78e-15；未更新PIDL仍E=0.0052684000、残差0.01348894、UV mass误差7.5487%、active加权relL2=6.120899／相关0.102518。新测量只提高了归因可辨性，没有缩小上述场差，也不提供物理真实性证明。

下一步优先核对A/B共有的局部导数公式、有限h跨支和近似驻点误差传播，暂不把SVD重建作为主修复方向；先利用现存记录形成一个有判别力的方案。未自动增加方向／步长、重跑或启动3000秒优化。继续保留B0边界参数化、约束Q4 damage路线、实际Phi复用及原阈值。

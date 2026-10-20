# PIDL frozen c20s4 profiled-hidden R2：真实导数首检停止

目的：在保持实际Phi复用、FEM damage、原UV边界、B0 Smooth Boundary与1e-10输出头梯度阈值下，判断隐藏方向／物理预条件是否能改善PIDL数值平衡和FEM场误差。

本轮：HQ根据已核实的直接人方托管授权，批准a3386967临时JSON竞态修复后的一个独立有限R2。源d866cd8da1c2e3ee3a23ccfd08ce22d9da6e4dba，原5449d5a9/R1的8.052633秒失败与已消费claim保留。GPU5 worker3711852实际运行，约79.918925秒全链（包括4.985126秒机械检查）后自然因AdapterStop停止。无OOM、遥测error=null、终态own live=[]。未启动candidate／witness／readout阶段，accepted hidden=0、FEM求解=0、历史提交=0；完整比较未完成。实际Phi复用指同一状态内使用已存实际Phi，有限扰动后的当前Phi仍按原协议重建并保存。

结论：源端点读数稳定、局部锚定图内算子自洽；但完整实际profile映射（隐藏扰动→当前特征基底→Newton头闭合→真实NN场）的导数未通过原准入。当前实现不可用于预条件效果比较；科学结果对候选改善／参数化上限均不确定，不能称PIDL已经逼近其全网络极限。

## 失败发生在哪

1. 三次同一源端点E=.005268400005223913，头g∞=3.3665696098916786e-11，场差和投影梯度向量spread均为0，初态直接复用源Phi，无SVD。
2. 两方向J/C/U/Q/Z伴随与native H=BᵀKB检查通过。这只证明所实现的局部锚定图内部自洽。
3. 第一个方向seed173、h=1e-6的完整实际profile ±扰动，两次当前基底rank均386；头g∞=2.5598999482678853e-11／5.287808927702253e-11，均小于原1e-10。真实网络与装入场的realization≤3.63e-13，边界差0，固定状态和finally回滚均有证明。adapter_observables里的rolled_back=false是finally前快照，应以独立rollback.json的true判断。
4. `(q(+h)-q(-h))/(2h)`与预测Qv不满足原`abs1e-10+rel1e-4*max(norm(Qv),norm(FD))`，worker_failure记为`profile_actual_full_profile_derivative_mismatch`。h/2及第二方向尚未执行，随后停止，没有自动重试。

关键缺口：reprofile_check在抛错前未将Qv、FD、error/scale写盘，故现有材料不能还原失配范数或百分比。不能用局部伴随误差、odd/even比值或场差替代它。

## 保留的基准与两次微扰

共同算子：原生Q4 2×2 Gauss点、同一FEM damage和原UV边界，固定c20第4子步峰值。表中两次微扰只是导数检查的未接受trial，不构成新PIDL结果。active为g(d)ψ+，relL2按共同Gauss权重，相对冻结FEM场；UV误差沿用同一冻结FEM参考。

|方法／状态|弹性能E|自由位移残差Ru|UV mass relL2|UV H1 rel|active relL2|active相关系数|
|---|---:|---:|---:|---:|---:|---:|
|冻结FEM参考|0.00432057602453|3.77600785e-15|0|0|0|1|
|PIDL原端点（未更新）|0.00526840000522|0.0134889412|0.0754865147|0.587638879|6.1208993|0.102517986|
|PIDL +h 未接受trial|0.00526839894542|0.0134888527|0.0754865044|0.587638832|6.12081816|0.102519549|
|PIDL −h 未接受trial|0.00526840106713|0.0134890297|0.0754865252|0.587638927|6.12098048|0.102516422|

本地独立NumPy回放三份PIDL已存场的E/Ru误差均<1e-12。FEM→PIDL原端点仍有同一场差，本轮没有改善它。保存的±场odd自由DOF L2=1.30567377756e-5、even=9.8451532214e-9，比值7.540285629e-4；这是一个h下的响应描述，**不是导数失配比例**。

当前原始特征矩阵条件数约5.2532e8、变换maxabs约7.366e7，说明敏感性风险；rank在cutoff×0.1/1/10均386只排除了本次观察到的离散rank跳变。动态保留子空间／坐标导数、浮点误差放大、近似头闭合与局部chart失配仍是竞争解释，不能认定唯一原因，更不能声称“漏了C”（局部图已经包含C）。

![冻结FEM与未更新PIDL的active场](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_profiled_hidden_c20_r2_hq_20261020/analysis/baseline_active.png)

共同symlog色标（1e-5以下线性）显示旧场差：FEM热点与PIDL沿预制裂缝的高值分布不同；这不是新优化结果。

![已存正负扰动的实际位移响应](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_profiled_hidden_c20_r2_hq_20261020/analysis/finite_profile_response.png)

共同线性色标显示实际odd位移响应在预制裂缝附近较强，even分量较小。因缺少当时Qv，不能把此图称为导数误差定位图。图像已逐幅检查，说明与来源保留在同stem sidecar。

## 预算、资源与取回

总链79.9189249秒，机械4.9851262秒计入原首300秒和总3000秒；controller78.8220487秒，worker存在区间约73.47秒是GPU占用时间上界，不能当CUDA kernel time。没有完整CPU/kernel分项或费率，不虚构金钱成本。5次密集头H装配累计约3.025秒；其余时间无法精确分摊。

实际保守计数：{"energy_force_field": 78, "hidden_jvp": 12, "hidden_vjp": 15, "C": 7, "CT": 6, "native_tangent": 15, "head_assembly": 5, "head_factor": 5, "head_triangular_solve": 26, "raw_feature_forward": 86, "explicit_head_products": 20, "svd": 2}。energy_force_field是该实现记账项，不等于78次PDE求解。峰值RSS=3243081728bytes、CUDA allocated=10541088768、reserved=11700011008、任务存储=1170972148；首检未全过，不能据此证明完整生产容量或性能天花板。

远端426项共1,170,977,731bytes逐项SHA/大小及覆盖核验，manifest SHA=6b5b2bf65640c02eac6b3a67834e2a3baf53d517748eff128341a4e761870d3b。compact传输402,708bytes，旧本地相同SHA复用37,251,187bytes；大Phi/checkpoint/raw NPZ仍在远端，**不是完整本地镜像**。另1,921,571bytes无损bit-XOR传回实际UV，重建后逐数组SHA一致，远端只读codec CPU .38635秒／传输wall21.29994秒。本地仅4份唯一保存状态回放，图像修复共3次渲染／12次轻量保存场回放，无NN/Phi/SVD/切线/求解。

## 决策与后续

停止当前profiled-hidden实现，不把剩余时间自动转为新尝试。保留已验证的共同Q4算子、实际Phi稳定复用、固定端点及约束Q4 damage路线。

下一项应先做观测完整性修复：每个方向／h的xi、Qv、实际±字段引用、FD、error/scale/tol、rank、realization及回滚证明在判门前写盘，再研究动态子空间与原始头病态放大能否解释失配。此处只是下一步设计，没有改阈值、重新扰动或启动训练。只有导数可信后，才有依据继续原定能量／梯度／Ru／active／成本的预条件对比。

本地case：[回执](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_profiled_hidden_c20_r2_hq_20261020/execution_receipt.json)；紧凑记录：[目录](pidl_profiled_hidden_hq_r2_result_20261020/)；分析脚本：tools/s04_e011_analysis/analyze_profiled_hidden_stop.py。独立结果风险审查另存review.json；此前所有FEM/PIDL结果与已消费授权保持不变。

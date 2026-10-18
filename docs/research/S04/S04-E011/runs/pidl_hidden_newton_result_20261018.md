# E011 c20 hidden-feature adaptation plus Newton head — result

目的：检验允许PIDL隐藏特征改变后，能否突破上一轮固定特征的同弹性能限制，并同时检查FEM场与平衡误差。

本轮仅c20峰值s4/rawstep99，U=0.11999988；86,756节点/86,408原生Q4单元/2×2GP，E=1、nu=0.3、eta=0。FEM参考为独立重启后接受的条件峰值outer18，并非修复后的完整演化轨迹。

做了什么：从上一轮实际固定特征Newton网络出发，完成4段隐藏层L-BFGS＋Newton头校正；311次能量／梯度计算、152.82秒、15次稠密切线组装／15次求解、47次显式切线向量乘积。400次／600秒等上限未放宽；正常四段结束，无重试。

| 方法（均为c20s4，固定FEM damage） | 弹性能 | 位移残差Ru | 位移场相对L2 | 梯度场相对H1 | active相对L2（倍） |
|---|---:|---:|---:|---:|---:|
| FEM c20峰值（固定参考） | 0.004320576025 | 3.77592e-15 | 0.0000% | 0.0000% | 0.000000 |
| PIDL 原UV＋FEM damage | 0.01121651498 | 0.0196012 | 3.7394% | 111.9818% | 51.780708 |
| PIDL 上一轮全网络 L-BFGS | 0.005401565679 | 0.0159958 | 6.2627% | 59.1347% | 6.334879 |
| PIDL 上一轮固定特征 Newton | 0.006024051981 | 0.0209761 | 13.8297% | 80.8074% | 3.800723 |
| PIDL 本轮隐藏特征＋Newton | 0.005683523868 | 0.0156433 | 10.9404% | 71.7668% | 5.348757 |

结论：相较固定特征Newton，本轮PIDL弹性能下降5.65%，Ru下降25.42%，位移L2误差由13.83%降至10.94%，H1误差也下降；但active相对FEM误差由3.8007倍升至5.3488倍（增加40.73%）。

本轮PIDL能量仍比上一轮全网络L-BFGS高5.22%，其位移L2/H1误差也更大；本轮Ru及active误差则更小。各项排序不同，不能宣布一种方法全面胜出。

| PIDL方法 | raw Eel 隐藏参数梯度∞ | raw Eel UV头参数梯度∞ | 头部驻点检查 |
|---|---:|---:|---|
| PIDL 上一轮全网络 L-BFGS | 0.24650393 | 0.0044164448 | 原387子空间仅386可辨识；本项不强行求值 |
| PIDL 上一轮固定特征 Newton | 0.12857237 | 6.1594677e-13 | 旧固定坐标3.3461e-11，达标 |
| PIDL 本轮隐藏特征＋Newton | 0.87655074 | 1.3164394e-13 | 当前坐标7.1364e-11，达标 |

固定特征的能量限制确实可以通过隐藏特征调整突破（实际降能3.405281e-4，大于预先规定1e-10）。本轮实际头部投影梯度∞=7.1364e-11，满足1e-10；隐藏参数梯度∞=0.876551，并未接近零。四段预算结束不代表全网络收敛，也不能据此判定整个8×400架构容量不足。

梯度三类空间分开：raw参数梯度、质量归一后的头部坐标梯度、全局节点位移残差；不能用其比值分配物理贡献。固定特征旧坐标已闭合，本轮重新白化后该同一旧端点的∞范数为1.000635e-10，∞范数随坐标旋转变化，不重判旧结果。PBD旧387方向当前仅386数值可辨识，辅助conditioned梯度标不可用；raw梯度、能量及场比较仍完整。

力学目标始终使用同一FEM damage和原位移边界，damage输出行与Smooth-B0 anchor参数保持不变；共享隐藏层可能改变未参与本轮目标的NN damage输出，因此本轮不能证明damage预测或演化正确。历史提交0、演化步0。不同起点和实际工作量不支持等预算优化器排名。

补充事后检查：独立回放全部9个已保存接受点（初态＋四对隐藏层／头部端点），不新增求解或改变主要判据。四次Newton头校正均在相同当前隐藏特征、FEM damage与边界下，降低能量但增大active相对FEM误差：

| 固定当前隐藏特征的Newton校正阶段 | 校正前active误差（相对FEM，倍） | 校正后active误差（倍） |
|---|---:|---:|
| PIDL c20头校正1 | 3.324362 | 3.977105 |
| PIDL c20头校正2 | 3.704618 | 4.356522 |
| PIDL c20头校正3 | 4.268677 | 4.934080 |
| PIDL c20头校正4 | 5.172940 | 5.348757 |

这表明在本轮受限神经试探空间内，积分弹性能降低不保证局部active场误差单调降低；不说明FEM与PIDL的物理能量算子矛盾，也不作因果百分比分配。

下一项建议：从能量更低的上一轮全网络L-BFGS端点出发，按该端点当前特征重新构造数值可辨识输出头空间，再做Newton校正。先区分初始化／参数条件性与特征限制，仍固定同一FEM damage和边界，保留B0及约束Q4 damage路线。本轮预算已结束，未另启此项求解。

Execution: source `ccc011f02a9f697eb30315dacd0e13598b45cf6c`, Taobo GPU5 PID2828295 exited normally; 76files/144716430bytes retrieved with count/per-file-size verification. Probe performed actual hidden backward and tangent assembly/solve with0updates; peak5,652,556,800bytes, no finite/contract failure. Full outputs and five inspected figures (including the posthoc stage supplement)/README/sidecars: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_hiddennewton_ccc011f_20261018T121350Z_production/analysis_hidden_newton`. Independent saved-tensor audit confirms24/24hidden tensors changed (maxabs1.5275642e-4), damage output row exact and UV-head increments remain in the old raw387span (outside-span norm4.2304e-12 versus floating-point identity bound4.0785e-10).

Independent field replay, exact damage and boundary checks passed. Code review14tiny fixtures; analysis review independent of author. Final independent evidence review passed. Preserve frozen E003/E011/PBD/UVHEAD/Newton results.

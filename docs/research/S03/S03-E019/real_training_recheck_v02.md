# E019-D03 v0.2 — Pro采纳与实现冻结附录

2026-10-17；本附录与[原v0.1](real_training_recheck_plan.md)合并为当前方案。
v0.1及已发送正文原样保留。依据[Pro完整PASS_PLAN](real_training_pro_reply.md)，
只明确构造/检查/表示，不更换输入、算法、阈值或目标。当前只准备代码，
不执行测试、真实读取、QR/SVD、求解或绘图，不改旧产物。

## 必须落实的构造边

1. 保存R及第一次QR的C_H；正权重、坐标有限、加权中心二阶矩m2>0，
   平移与旋转解析独立。旋转列仍为(-dy,dx)，不改变原R的列尺度。
   核DR=H C_H及H全Gram，不数值找秩/第三次QR。
2. 白名单源→S/F/D/R/U0→A/y/b全部可重建；保存原允许的源数组、stencil、
   free/boundaryDOF及U0、模型z_k。核U_k−U0=Fz_k、采样及b_k=A z_k。
   原节点场只核来源/BC/采样，不能声称重新认证平衡。
3. 保留奇异对双侧核AVr=Lr sr、AᵀLr=Vr sr及Lr/Vr全Gram；不能用修复U
   替代Lr。全L/Vh不保存，则全SVD重构/全Gram仅producer自检，不是独立全谱认证。
4. 逐臂先核Q和U像内，再核残差加法/实际交叉项以及保存Jk=JQ+gap²。
   b在A像内不意味着在截断像内；失败只阻止该三场账本，不直接判源场非法。
5. 理想精确A=QDSF及s>0推得QLr=Lr；实际有限精度仍逐项检查。不强求
   同次legacy失败或新残差降低。r改变暂停身份解释，不强制匹配1203。
6. 图固定画D^{-1}r_new和D^{-1}r_k的原648点U/V散点，8面板共同对称色标；
   单位mm，原点坐标，无插值/删点/平滑。只有展示去权重，验收和mm²账本
   全使用加权向量。RMS_Q=sqrt(JQ)为加权向量RMS，不额外除n或2。
7. Uᵀr单位mm，用1e-15向量容差；Gram/UT/A等无量纲1e-12；平方/交叉项
   mm²用1e-18；rtol1e-12。eta≤.5无近似豁免。

## 独立核验与预算

新producer用np.einsum(...,optimize=False)；独立核验模块不导入producer，
自行重建CST stencil/free/D/R/U0和A/y/b，用scipy.linalg.blas.dgemm全量
Gram、UT、双侧奇异关系和构造矩阵交叉核对；不得抽列或调用producer差异。
完整向量p/r、新旧路径、b像内/残差及低秩Q用独立math.fsum（已舍入float乘积）
和Decimal.from_float、localcontext.prec=80逐项乘加核对；不替换候选。
Q向量数值或通过状态跨路径不符专属REFERENCE_PATH_UNRESOLVED，ratio不单独相等。
其他向量/矩阵不符按原容差停止。独立验收单列60秒软预算，若不够即停，
不承诺任何精度路径必能在60秒完成；预算准备不等于已验证。

生产60秒从首次输入处理之前开始，覆盖加载/构造/1SVD/2QR/全量自检/输出/
图/哈希/收据/最终检查。A人工单元（stub，0实际QR/SVD）、B同尺寸人工
资源试验（1SVD/2QR并含全部产物）、C真实生产与D独立验收分别审批。
任何首个非预期异常/警告/预算失效即停，不重试。未完成目录不得当成功；
成功收据最后追加确认标志，最终预算不通过不写完成标志。

未来C需逐项批准两项opaque哈希：training_geometry.npz与frozen_predictions.npz，
只原字节、不解码；其余准读文件/键沿v0.1。未批准哈希不调用旧全包load，
不默认为来源通过。当前不核实际文件可用性、不读任何数组/来源收据。

## 对反演的作用

本轮只恢复可信的训练侧数值诊断；后续仍拟合原y，不把p当去噪真值。
即使候选b(q)不在保留像内，原J(q)仍可定义，只是不能套该平方账本。
G=∂b/∂q与独立物理约束另审；当前不输出q/相场/材料/疲劳参数。

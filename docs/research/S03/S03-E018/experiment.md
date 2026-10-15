# S03-E018 — 训练主剖面的观测算子与模型表示一致性（待确认）

2026-10-15，protocol draft v1，Storyline S03。当前仅准备方案和独立只读审查，
未实现新分析或计算真实场。E016/E017原协议、预测、分数和结论均不改变。
动机来自已知E017结果，属于事后诊断；训练侧检查不是新的独立验证。

## 1. 最小问题与可改变的决定

在已有主开口剖面上，模型—DIC差别中，多少取决于“直接CST采样”与“复用DIC
插值权重采样”这两个表示接口？按同一接口比较后，法向或切向配对响应是否
仍有偏离？先检验这个接口，再决定是否需要模型/状态或独立观测依据。

Claim class C1，controlled-experiment；一个试件/cycle292018.5、stage14-stage13
训练增量。不是新cycle预测、真实裂尖/相场/材料反演或观测噪声识别。
37个剖面位置并非独立重复，不作显著性、噪声界或物理成功阈值判断。

E017的646点MAE差距只用于选择“先看主条带”的下一步；本剖面新度量不能
直接分摊或解释原MAE差距，更不能宣称算子改变使原高载预测改善。
固定条带边缘的对称剖面也不代表B带全部301点或真实裂缝过程区。

## 2. 只用训练与已保存静态场

项目local_archive/experiments/S03-E016：

- R001/prepare：成功回执和全部4个PREP文件。prepared.npz保存648个训练点、
  train_v/weights/XY/mesh/tri/boundary/bc；training_geometry.npz保存39970个
  原联合有限训练facet的IDs、stage13 XY/XYZ和stage14-stage13 DeltaUVW。
- geometry_audit.json主b=3.6剖面保存的106个query、每点4个neighbor ID/coeff、
  rank/support/距离、原53点raw opening。沿preparation.json记录原载荷身份。
- R002/fit：成功回执、fit.json、solved_fields.npz的old/proxy/intact完整节点场
  及各*_sampled；frozen_predictions.npz只作原FIT完整哈希绑定，不分析高载预测。

锚点：R001 receipt8655d49b30e341d488eeb8c15db9a7d347f236634a22adbbf39fcb7b4bbd3ccf；
R002 receipt3173f0f659d6e451f7fccc39a4ca0973ae3caad750c9d98ce754a1bcec325674。
保持既有完整来源链/runner与依赖/产物SHA；前后核验旧文件不变。

不读取原ZIP、任何nodemap、R003真实目标/残差、E017逐点文件或其他stage/cycle/
新留出。当前方案审查也不打开真实NPZ；仅查文档及源码字段可支持性。
不重跑prepare/fit/validate/旧render，不求解、改mesh/BC/damage/q/nu/E/宽度/
端点、邻域重选、重新拟合背景或按误差筛点，不联网/SSH/发送/push。

## 3. 固定剖面与索引

使用原主带b=3.6mm，不用病态辅助1.8mm或其他带替代。
x_i=0.9*i，整数i=-18..18，共37对(74query)，都位于原人工patch内部。
这是原53点i=-26..26的既有子集：原数组索引i+26，上侧该索引，下侧53+该索引。
按整数位置选择，不用误差或浮点阈值选点，不移动y=0/转角/峰/端点。

复用这74query保存的neighbor ID和coeff，不重新找四邻或回归权重。
对training_geometry的原facet ID建立唯一映射，不用“ID-1”索引联合有限子集。
核对prepared的648点是该训练集合的同ID子集，XY和du[:,:2]==train_v。
阶段13坐标唯一；不平均参考坐标、不重施导出对齐header。

保存的query必须supported、rank3、4neighbor/coeff有限、原距离<=2mm；
核对各邻点在规定同侧，sum(a)=1且sum(a*XY)=query（仿射再现）。
邻点及query必须在原36x18mm网格内；任一点不满足即停，不外插或丢点。
原负插值权重如实保留，不重归一化成凸权重。

## 4. 同一模型的两种取样，与DIC并列

T_FE为原sample_regular_mesh的固定对角CST插值；只采样已保存节点场，不装配
刚度或求解。核对原41x21/861node/1600tri网格语义及T_FE(U_k,XY_obs)与已保存
*_sampled一致；不替换旧采样结果。对每个query q：

```
D(q)          = sum_j a_qj * DeltaU_DIC(ID_qj)       # 同时处理U/V
M_k_direct(q) = T_FE(U_k, q)
M_k_match(q)  = sum_j a_qj * T_FE(U_k, XY(ID_qj))
```

三机械臂old/proxy/intact全部报告。同一组query/neighbor/coeff用于DIC与模型。
matched不是重拟合模型，也不是把实测残差加回模型；无blend/最优比例/搜索。
D的法向raw upper-lower须复现原主剖面opening_mm的37点子集；切向量是由同一
保存权重作用于现有训练U分量得到的新诊断量，不声称它原来已被验收。

## 5. 刚体转动与“切向”的语义

固定坐标x为切向、y为法向，这是沿用原线方向，不是独立测得真实裂缝局部坐标。
未经补偿的上下U差受转动影响，不能直接称为滑移量。

仅用训练侧完整648点与继承面积权重构造同一全局刚体子空间，不用E017的646点
掩模。对DIC train_v及每组模型*_sampled分别计算同一线性投影的转角系数theta_X。
这不是材料参数拟合，也不是分别调整观测算子；不用header角度重施变换。
按加权质心r_i=(-(y_i-ybar),x_i-xbar)：

```
theta_X = sum_i w_i*r_i dot (u_Xi-ubar_X) / sum_i w_i*||r_i||²
J_n[X](x) = v_X(x,+b)-v_X(x,-b)
J_t[X](x) = u_X(x,+b)-u_X(x,-b)+2*b*theta_X
```

平移在配对差中消去；刚体转动在J_n中本来消去，在J_t中用+2b*theta抵消。
同一模型的direct/matched使用同一个theta_k；DIC使用theta_D。不得针对37点、
上下侧、区域或采样接口重新估计theta。CST与DIC权重仿射再现确保同一刚体场
在两个接口上具有相同值；必须用合成平移/转动/仿射场测试这一点。

报告的是全局刚体补空间下的配对相对位移，不是独立物理裂缝滑移真值。
使用raw主开口量：不做14点背景重新拟合、不减原DIC背景到模型、不平滑、
剪负值、改符号或重新量半高裂尖，避免不同处理制造“形状一致”。

## 6. 只做代数与描述性比较，不换原指标

令配对向量J=(J_t,J_n)，对每臂、每x：

```
r_direct = J[M_direct]-J[D]
r_op     = J[M_direct]-J[M_match]
r_match  = J[M_match]-J[D]
r_direct = r_op+r_match
```

逐点保存有符号分量和恒等式误差。37个等间距位置等权，不将648点面积权重
强行移到剖面。面积权重只用于648点的全局刚体子空间。新剖面范数不是E016/
E017面积加权MAE，不能当作原排名/结果的替代。

描述量只报：每分量mean_abs(r_direct/op/match)，以及向量
L_direct=mean||r_direct||、L_match=mean||r_match||、L_op=mean||r_op||。
接口净差额A=mean(||r_direct||-||r_match||)=L_direct-L_match。
禁止把L_direct当作L_op+L_match，禁止用百分比硬分“原因贡献”或以抵消制造归因。
没有强制“某分量更大就是原因”的门槛；近算术容差的差异只标数值未分辨。

| 观察 | 可改变的下一步 | 不允许结论 |
|---|---|---|
| 来源/仿射再现/旧采样/原开口重构不符 | 停止，另审最小接口核对 | 不改旧结果、不自动重试或换带 |
| direct与match在算术上相同 | 该接口差异不能解释本剖面偏离，转看同接口模型响应 | 不排除全部观测误差 |
| A非零或op分量可分辨 | 记录接口定义影响剖面比较，先明确后续观测定义 | 不称作高载误差原因或新物理改善 |
| match仍偏离DIC | 同一空间取样下既有模型与训练观测仍不同；按法向/切向记录 | 不唯一归因材料/边界/噪声/三维，不直接加q |

本检查不能确定最优参数、噪声底或FEM空间的最佳拟合上限。若后续需要运动学
表示上限/物理模型修复或独立观测，应另立方案和新验证依据，不能调stage15。
训练开口也曾参与定义proxy先验，因此该剖面一致性不是独立几何验证。

## 7. 规模、最小图与停止规则

拟新S03-E018-R001，当前不创建。单线程CPU、一次离线分析、软60秒覆盖
输入核验、采样、剖面/算术、绘图保存和最终哈希/成功收据；0次求解/调参。

产物最小集：一份37点三臂可复算表/NPZ及全局描述表，来源/算术/输出收据；
两张PNG/PDF与同名说明、README：

1. normal/tangential两行、三机械臂三列；每格DIC、direct、matched三条线，
   同一坐标/单位/37点，法向或切向跨臂同尺度，明确全局转动补偿；
2. 同样六格展示r_direct/r_op/r_match，有符号零线、共用对称y尺度，不裁点。

不添加目标导向的案例/排序、局部放大、变带或额外场。图只解释该配对观测。
仿射权重矩用atol1e-12（sum无量纲/坐标mm）和rtol1e-12检查；位移/剖面恒等式
用rtol1e-12、atol1e-15mm；均为算术容差，不是物理接受门槛。
任何新警告、非有限、越界、身份/算术异常、输出失败或超预算即停，取证保留，
不重跑旧prepare/fit/validate/render，不静默修正源文件或切换数据。

## 8. 当前审查与授权

请独立只读Codex审查：字段可用性/ID映射、37点与原权重复用、CST采样域、
刚体转动符号与公共648点投影、误差恒等式/范数不可加、解释边界与最小规模。
仅读方案/既有源码和结果文档，不加载真实NPZ、原文或计算新剖面。
通过后先展示方案供用户确认，再准备代码/合成测试/独立代码审查与确切命令。
无方案审查或人方“推进”自动转换为真实分析/求解/外发许可。

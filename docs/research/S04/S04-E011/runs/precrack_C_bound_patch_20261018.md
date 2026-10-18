# C200 物理越界诊断及可选硬约束补丁

S04-E011 / Run pf_s04e011_abc_20261018T115520Z；仅重读已保存C场及其自身固定U0下界，无网络推理、训练、历史提交、新FEM或轨迹。原A/B/C的58.34%组件改善及其限定不变；本诊断不增设或改写r2准入条件。

| 指标 | 物理节点场 | 原生Q4 GP4物理重构 |
|---|---:|---:|
| d最小值 | -1.63859615e-4 | -1.57593209e-4 |
| 最大回退 max(h0-d,0) | 1.86592340e-3 | 5.54162766e-4 |
| 超1e-3回退 | 5节点；lumped面积0.00188895% | 0 GP；面积0 |
| 上界超1 | 0 | 0 |

负值最深节点位于(0.0290011,-0.0113605)，GP位于(0.0285960,-0.0117623)；最大回退节点位于(-0.2598831,0.0011542)，GP位于(-0.2595987,0.0009798)。5个超1e-3节点的完整坐标见同目录precrack_C_retreat_nodes_20261018.csv。

负值幅度超过float32单位epsilon(1.19209e-7)的GP4加权面积占97.70239%，大多是初始完好背景上的浅负偏置；负值幅度积分2.56243e-5。只看初态h0>epsilon处，回退超过epsilon的加权面积仅0.0340525%。这一区分避免把背景负值统称为已有裂纹愈合。面积是同一原生4点Jacobian加权估计，不是连续level-set精确面积；节点面积是另报的lumped指标。

## 浮点量级与现有容差

初始C映射实测误差=0；FEM float64→float32最大差2.97129e-8、初始逆映射残差1.49012e-8。对同一已保存场的GP float32/float64重构差为1.08155e-7(d)、9.11221e-8(h0)。因此约1.58e-4的GP负值、5.54e-4的GP回退显著大于这些舍入差，是真实物理场越界，而非未经映射的网络raw输出；本次并未取回/推断raw。

所有负值、所有GP回退幅度均小于1e-3，故不触发旧的宽松box量级筛选；5个物理节点回退超过1e-3。严格非负/不可逆条件以及现有native-Q4 QP contract默认1e-10可行性尺度并不满足。后者是对照物理约束的尺度，不把旧r2改判为正式硬可行性试验。PIDL tol_ir=.005只设置gamma16875，FEM tol_irrev=.001只设置gamma421875；它们不是可把上述回退自动判为已收敛/可接受的后验豁免，phase/staggered4e-4也不是bound容差。

## 最小可用补丁：前向中限制物理节点场

`source/nodal_damage_alignment.py`仅新增显式`hard_lower_box=False`选项，默认逐位保持原C和旧checkpoint契约；不修改任何runner/config或W0/W25。

```python
adapter = NodalDamageAlignment(
    xy, mode="fem_initial", initial_damage=d0,
    raw_reference=frozen_raw_theta_R, expected_crack_mask=crack_mask,
    hard_lower_box=True,
)
```

新选项在原锚定映射之后、所有原生Q4能量/空间梯度之前计算`d = clamp(d_candidate, d0, 1)`，再强制原251节点d=1；下界是该块固定已声明的初始场，不更新历史。d0=1的节点输出恒1且raw梯度0。Q4形函数非负且和为1，所以节点d>=d0、d<=1保证整个双线性物理场(包括GP4)不低于插值下界、且不超1。它比只约束4个GP的条件更强，不能宣称与FEM约束试空间等价。

C的精确初态保留；d0<1的可演化节点在初始边界采用torch.clamp实际autograd选择，raw梯度仍.25，越界饱和时梯度为0，等式处仍为非光滑映射。浮点溢出在投影前拒绝，不能被clamp掩盖。新约束标记写入mapper extra_state，默认旧状态格式完全不变；旧/新约束checkpoint不能默默互换。将来必须仍在同一不可变theta_R、同设备/完整节点forward上取原始锚，不得在已训练theta上重锚。

## 检查及使用边界

46项确定性map/bounds/parity检查通过，无optimizer调用。全86756节点/86408格/345632GP的已保存C物理候选做代数回放，scalar映射反演回放误差0；新选项使节点及GP上下界违背均为0、初态精确、251硬线不变、原可演化节点初始raw梯度.25，显式状态roundtrip一致。代数回放使用dummy零raw origin，不是网络/实际GPU checkpoint回放。仅验证补丁数学可行性，没有保存投影后预测、重新计算FEM精度或冒充训练改善。

该选项改变试空间，并使固定下界的软Ehist项不再活跃；它不是改loss权重，也不保证收敛/位移平衡、尾部改善或FEM误差继续下降。当前只保存补丁，等待W0/W25结果后合并选择一个最小后续动作；本轮无新增数值验证预算或执行。

数值与原图源：local_archive/experiments/S04-E011/runs/pf_s04e011_abc_20261018T115520Z/admissibility_final/；其中summary.json、patch_check.json、C_physical_admissibility.png及sidecar可复查。焦点代码/证据复审收据另存，不替代后续训练验证。

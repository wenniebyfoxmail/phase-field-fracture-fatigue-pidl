---
storyline_id: S04
experiment_id: S04-E029
protocol_revision: v1-smooth-current-lower-increment-20261018
status: preparation
---
# E029：只修E028的damage局部零梯度表示

独立新试验，E027/E028完整冻结。Owner沿用本对话。最新直接人方已授权有GPU继续最小修复路线至实际场图/数值（总部userMessage01a150b4-280e-7200-8b5c-c1ab9a18e6ac及后续“FEM那边也推进到修复前后的场图和数值对比”），总部在E028终态后明确只修可行增量表示，不为一般预算另等批准。必要焦点复核后进入新鲜目录单次Run，具体首停不重试。

## 已知瓶颈与不再重复的计算

E028最终B/R全86756节点d精确等c20s3 lower，target有4115节点增长。保存的10/50/100/200检查点均显示86465可变节点100%低于投影下界。只读producer真实模型复推与autograd确认，B/R终态可变域及目标增长域 `dd/dNNraw=0`，raw到lower阈值最小上侧间隙分别仍为-16.7334/-15.9640，非舍入边缘。证据在parent_saturation.json，原模型hash和向量路径可追溯；未保存中间步不推断连续饱和。物理界保持但当前增量无法由damage自己的局部误差梯度学习；共享UV参数仍可间接改变raw，不称永久数学禁区。

最小修复仅改变damage表示，直接比较冻结E028-R的既定同S1500起点、fresh Adam1e-4、seed1、200步、Lsup+wA*LA与新R；不重跑旧R、不增加新B、不改网络激活/宽度、损失、采样、学习率、优化器或目标。

## 唯一选择的真实可微增量映射

令h为真实c20s3已提交lower，固定251预裂纹及h=1节点恒置1。theta0为精确原S1500；r0为其冻结同节点NN raw第三输出，dseed为E028同一S1500的前向可行投影。对h<1的可变节点：

`p0=clamp((dseed-h)/(1-h), epsilon, 1-epsilon)`（只在初始化一次），`z0=logit(p0)`，

`d_theta = h+(1-h)*sigmoid(z0+asinh(r_theta-r0))`。

epsilon固定1e-4，不扫参。它是内部初始化余量，不是新的物理下界；运行中的p可以低于epsilon。新0步对旧mapped0的逐节点变化<=epsilon，已实值检查最大1.0000000000000017e-4；global d RMS从.00186763变.00186963，active .77277112变.77272689。完整0步变化表在map_check.json，生产前须原样复放，不将这一步算训练收益。

无STE、预测clamp、detach梯度替代或目标作lower。asinh只压缩相对raw的大偏移，不改MLP激活；选择依据是已观测raw偏移达约40，直接logit线性平移会指数衰减导数，asinh相对尾部为代数衰减。所有导数使用真实autograd，固定节点导数0，可变节点初态非零。r0/z0/h/ordered xy均为冻结buffer，不能用训练后的网络重锚或更新历史。

硬界由公式保证，原生Q4非负形函数保持插值lower/upper。新表示对有限参数一般在可变节点取严格内点，不承诺有限参数精确达到target的0/1；物理界不放松。数值全可变域导数再次全部变0则首停，不以“解析上应为非零”掩盖实际浮点饱和。

## 运行前梯度流证据

8项纯合成/确定性检查覆盖物理界、固定点零梯度、真实AD/有限差分、正增量损失下降方向、旧平坦区对照、实际fixture参数梯度与UV逐位不变、冻结buffer/状态身份、非有限/全域数值零导数拒绝；无optimizer.step或训练loop。

同一86756节点/86408Q4静态代数回放：新0步全部86465变量及4115目标增长节点的真实导数非零，增长域99.9757%导数>1e-8；使用已观察B/R的raw向量作压力输入时仍全部非零、约97.3269%增长域>1e-8。节点/GP界和预裂纹全保持。1e-8仅说明导数量级，不是物理有效性或学习成功门槛。这些是保存raw的counterfactual映射检查，不是E029训练场，不据此宣称修复成功。

## 固定小试、主读数和证据

synthetic已暴露单状态c20s4/horizon0/seed1，限定C2近似状态拟合；同四MAT及true lower、f/history冻结，不读留出或新状态。新R从同一原S1500网络、空Adam1e-4(.9,.999,eps1e-8,weight_decay0)、CPU采样generator seed1出发，200步2048 global+2048 Z，float64。目标仍为E028-R的LU+LD+wA*LA（wA为同一stopgrad .25梯度范数cap且<=1），机械权重仍0。唯一候选改动是上述damage映射及必要冻结origin buffer。

**唯一探索主读数改为本次R200/R0的Z active相对误差比**，方向容差1e-8、分母<=1e-12为NA；避免再次只击败已漂移的弱终态就宣称成功。与冻结E028-R200、旧原S/C、旧共同初态、旧mapped0及新smooth0同时报告。旧E028的R/B判据不动。参考replay近0与已有初始分量说明方向性改进有空间，不设未校准显著性/改善百分比门槛；单单位不造CI。

0/10/50/100/200完整global/Z u、v、UV、d、raw/active、force/reaction、节点/GP bounds/healing/precrack、d-h增量；保存raw/相对原点、真实局部导数非零比例及>1e-8比例（全部变量及增长域）、实际参数梯度范数/夹角与active权重。新增训练前后d差及目标增长域拟合变化，不能把epsilon带来的正值当作学会增长。0/50/200保存同节点场，终态存MLP/Adam/RNG及映射buffer；实际优化trace不作物理演化。

同尺度图必须含FEM、旧共同初态/原S/原C、旧mapped0、冻结E028-R、新smooth0与新R的u/v/d/raw/active及有符号误差，另列primary固定端点与实际成长/约束代价。完整数值表和图在取回后核对、目视复核。若只恢复梯度或优于旧R却劣于新0步，明确是组件能力/部分收益，仍不能叫有效训练修复。

## 有限成本和停止

本次只1GPU、200新更新；**<=.5GPU小时（1800秒，包含准入、预检、评估、保存）**，仍小于用户本轮2GPU小时上限，不要求耗满。外部1790秒TERM+5秒KILL，内部1800秒；32GiB RSS、2GiB输出。GPU初始free>=20GiB，allocator<=实际free−1GiB且保留1GiBheadroom，实际UUID核对；共享他人进程不动。预检仅3次真实backward、无step，1.5倍更新成本+300秒评估保存余量必须在上限内。

数据/模型SHA、GPU、source/dirty、原S及新0步复放、当前lower任一不合，非有限值/梯度/参数、全变量数值零导数、物理界/预裂纹误差>1e-10，或时间/存储/RSS/显存触限，整次首停，不换映射、不扩预算、不重试。一般性能波动由预先固定200步判读，不临时改门槛/学习率。

结果图/数值实证后再判断：active与damage增量拟合是否保住或超过新0步，哪些UV/force代价仍在；无自主演化、FEM全教师、跨状态/真实道路或泛化结论。若仍无收益，保存该单因素结果，再由HQ选择下一有证据的行动，不盲扫。

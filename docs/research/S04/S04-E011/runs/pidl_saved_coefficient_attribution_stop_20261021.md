# PIDL保存量系数归因：推导准备完成，本地AS控制阻断执行

**目的：** 在已有冻结二次能量profile上，把原PIDL Q−FD分解为解析AD与系数割线差、有限步B/H交叉项、真实端点缺陷、观测affine-consistency残差和离线场重建／闭合余量；不新增扰动、NN/AD、物理算子或训练。

**本轮：** 完整公式、74份原数据的SHA身份表、只读CPU脚本和一次性SSH入口已准备，源`feef73bd`，同一原reviewer完成聚焦静审。实际调用却在Mac客户端第3行`resource.setrlimit(resource.RLIMIT_AS,(16GiB,16GiB))`抛`ValueError: current limit exceeds maximum limit`。该行在card/source数组读取和SSH subprocess之前，故没有SSH、远端CPU分析、Phi读取、线性求解或新数值归因。不是一次新的导数检查失败，也没有观察到实际OOM。底层平台原因未验证，不据此猜测服务器或内存现状。

## 已审的完整分解是什么

令q_s=r_s+B_s z_s，w_s=z_s−z0，δx=(x+−x−)/(2h)，xbar=(x++x−)/2，保留各臂真实源z0及共同自由UV顺序。旧日志保存的是初始目标梯度d_s(z0)，不是绝对全局b；使用其真实RHS构造a_s=−d_s(z0)，而非从H_s z_s反造b并宣称残差为零。通过原源码、journal role、H/L、单步alpha1和z_s=z0−旧解识别RHS；初始defect没有另一份独立重复文件，这一来源限制保留。

定义e_s=H_s w_s−a_s、J_sec=δr+δB z0、cH=(Hbar−H0)δw+δH wbar，则

`H0 δw = δa + δe − cH`，

`FD = J_sec + B0 H0^-1 δa + (Bbar−B0)δw + δB wbar − B0 H0^-1 cH + B0 H0^-1 δe + δe_field`。

结合原Q_AD=J_AD−B0H0^-1U，可独立重构Q并分解Q−FD；e再拆成旧end_defect与观测affine-consistency余量。e_field比较旧GPU字段和新CPU chunk矩阵乘重建，包含本次离线算术，不能称纯旧producer误差。拟保留所有向量、未加权L2、带符号投影与闭合残差；分量可相消，范数不是互斥因果百分比分摊。完整[推导／代码与执行边界](../saved_coefficient_attribution_20261021/README.md)及[聚焦静审](../saved_coefficient_attribution_20261021/review.json)。

这套恒等分解能帮助定位已存算术链，但恒等闭合不等同于独立因果证明。真实全局b及实际浮点参数端点未另存，不用新checkpoint load或新扰动补造；参数化限制／优化停滞依然未判定。

## 执行、资源与费用

新授权`HQ-MESH-SAVED-COEFFICIENT-ATTRIBUTION-20261021`／human_delegated_hq，整项从2026-10-21 00:35:00UTC开始，硬1200wall/300CPU，截止00:55:00UTC。分配remote220、Mac client15＋SSH child10＋postprocess25=local50、review10、metadata reserve20；AS/RSS≤16GiB／0GPU。拟10向量解/20三角解/0新factor（允许上限12／2），**实际全为0**；源脚本SHA `ad17cf246fff617b6f9e1129aef7a941ad9707c4c2fb5699a7f7658d1c6b52e1`。

Mac CPU15秒设置先返回，随后AS设置异常；未验证AS控制成功。只读一次原limit为CPU/AS均[9223372036854775807,9223372036854775807]，并不能证明本平台可执行所请求设置。没有重复试设限制、换解释器、换host、绕过AS或发起SSH。服务器／GPU状态未查询，保持UNKNOWN。原数据根和原producer文件未修改，也无新结果可取回或绘图；本轮图代码仅准备，没有画空数据图。

本地入口失败CPU和全包CPU未逐进程实测，保留UNKNOWN，不记零；只读limit查询在其打印点self CPU0.031467秒，不能当全包CPU。科学数组读盘0、元数据／源码读盘UNKNOWN；新远端CPU／GPU／网络连接0。收口墙钟见[execution_stop.json](../saved_coefficient_attribution_20261021/execution_stop.json)。原R00231.532576秒科学／1199.566547秒precommit与更早全部费用和UNKNOWN保留。

## 结论与精确欠缺

本轮形成了完整分解推导与CPU脚本准备，**没有形成任何新的数值归因结果**。原四臂native约7.233／frozen约7.280倍FD允许值、共同失配和完整forward界不足的结论不变；FEM/PIDL端点、历史与3000秒优化状态不变。

执行前的精确欠缺是本机资源控制入口的可验证兼容性；当前没有已核验的替代机制。按已冻结no-retry控制收口，不暗去AS，也不把远端Linux限制冒充本地限制已经满足。后续修复设计需先验证资源控制入口，再在新准确授权下运行同一保存量分解；本次不追加测量或新运行。

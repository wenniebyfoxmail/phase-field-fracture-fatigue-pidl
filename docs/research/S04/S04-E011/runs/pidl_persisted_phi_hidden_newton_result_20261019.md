# E011 c20 actual-Phi reuse plus hidden/Newton continuation — result

**目的：**排除同一冻结PIDL端点重建基底造成的读数变动，再检查当前隐藏特征是否仍有可消除的同弹性能余量。对照仍是已收敛的条件FEM c20s4峰值（独立重启outer18），不是完整修复演化。

**本轮：**初态直接加载上轮audit保存的实际Phi/T字节，不重建、不SVD；三次完整网络读数后，通过原source/finite/tangent/solve/VRAM检查才执行两段隐藏L-BFGS和一致Newton UV头校正。仅隐藏变化后按原full401/cutoff重建并保存当前Phi/T；各阶段的矩阵、隐藏参数、完整模型和字段身份相绑定。无强制旧秩、ridge、阈值放宽或新尝试。保留原40calls/hidden block、10Newton/head、50assemblies/1000products上限与既有优化器设置。

唯一初始PIDL网络：`pf_s04e011_learnednewton_e2dc61d_20261018T125034Z_production/output/c20_s4/accepted_network.pt`；实际Phi/T字节来源为`pf_s04e011_readoutaudit_a698ec7_20261018T203915Z/output/c20_s4/bases/source/`。是同一已接受learned-head端点与其audit捕获矩阵，具体输入绑定见合同与compact审查记录。

Same state: c20s4/rawstep99/U=.11999988,86756nodes/86408nativeQ4/2x2GP,E=1,nu=.3,eta=0,float64. Mechanical FEM damage、原UV边界不变；Smooth-B0 damage anchor与damage输出行参数不变，约束Q4 damage路线保留但本轮没有damage求解。共享隐藏变化可改变未参与目标的NN damage输出。history/rollout/FEM updates均0。

## 同端点稳定性

三次保存实际Phi下的投影梯度∞均为3.3665696098916786e-11，低于不变的1e-10；完整投影向量、u/v/d逐项差均0，源弹性能误差0。生产初态也独立复现同Phi/模型/字段身份。初始Phi加载次数不等同新SVD，初始SVD=0。

探测36calls/6.53005s/0更新，真实切线组装及线性求解通过（相对残差1.00443e-15），峰值约5.38GB。该结果证实本轮保存/复用路径的读数稳定，不回填上轮未保存的失败值，也不保证任意重建或梯度变换路径相同。

## PIDL与FEM场比较

| 方法（同一FEM damage／原UV边界） | Eel | 全局Ru | UV相对L2 | H1相对误差 | active相对L2（倍） |
|---|---:|---:|---:|---:|---:|
| FEM条件c20峰值参考 | .004320576025 | 3.77592e-15 | 0% | 0% | 0 |
| PIDL前轮全网络L-BFGS | .005401565679 | .0159958 | 6.2627% | 59.1347% | 6.334879 |
| PIDL本轮初态：已学习特征Newton | .005268400005 | .01348894 | 7.54865% | 58.76389% | 6.120899 |
| PIDL本轮最后接受点：hidden2＋head2 | .005267089573 | .01352165 | 7.53965% | 58.71243% | 6.102823 |

相对本轮初态，PIDL弹性能下降1.310432e-6（0.0248734%），超过预定1e-10能量差；24/24隐藏张量改变，最大变化1.21510e-5。UV/H1误差仅小幅降低，active相对误差改善0.295317%，全局Ru反而升0.242523%。本轮能量仍高于条件FEM21.9071%；active误差6.1028倍是相对FEM的完整GP加权误差，不是差距缩小了610%。

active相关性.102518→.102732，积分.005265939601→.005264594916（FEM .004317519850）；raw ψ+相对L2 .719029→.718744、相关性.832043→.832724。raw在g(d)=0区不受退化拉伸能控制，作为辅助，不能替代active误差。

| PIDL执行顺序 | Eel | 当前保存Phi下g∞ | raw隐藏参数梯度∞ | active相对FEM L2（倍） |
|---|---:|---:|---:|---:|
| initial | .005268400005 | 3.36657e-11 | .0440131 | 6.120899 |
| hidden1 | .005267958906 | .0189763 | .160252 | 6.089510 |
| head1 | .005267646631 | 3.37737e-11 | .0249469 | 6.098213 |
| hidden2 | .005267301957 | .0229283 | .117380 | 6.111619 |
| head2（最终） | .005267089573 | 4.89326e-11 | .0258887 | 6.102823 |

全阶段按执行顺序保留，最终取最后真实接受head2，不按FEM误差选点。head1校正增大active误差、head2校正减小，能量则都下降；不能把积分能量下降等同所有局部场改善。两次隐藏变动都会重新打开头部投影梯度，Newton又将其压回原1e-10以下。

## 结论与下一项

实际Phi持久化/复用修复完成，本轮同端点读数稳定；允许隐藏调整后有真实但很小的降能余量。最终实际保存Phi下头部g∞4.89326e-11闭合，raw UV参数g∞9.94764e-14；raw隐藏参数g∞仍.0258887（比初态减41.18%）、全局Ru仍.01352165。因此只完成当前保留头空间的驻点检查，未证明全网络驻点或整个8×400网络的容量极限；原loss平台不能解释成FEM已被充分复现。

若继续本条纯神经力学块诊断，下一项建议比较更紧密的隐藏—Newton头耦合（如消去已求解头部后的目标／逐隐藏步校正），继续使用固定FEMd、原UV边界、保存实际Phi和共同场指标，检验当前分段更新是否限制进步；之后再决定是否需局部特征增广。该建议未启动新Run，不自动追加或转用剩余调用。原2段预算已按计划结束；不能用此次条件力学块替代damage/历史/疲劳演化验证，B0及约束Q4路线均保留。

## 核验与出处

生产正常退出：156calls/66.83944s，2hidden/head pairs，6dense assemblies/6solves/22explicit products，rank386，stop=two_hidden_head_pairs_completed，last=head2。旧35＋probe36＋production156=227<=400；当前轮耗时73.36949s，旧production耗时未知，未声称历史累计600s达标。无重试/外层状态回滚/非有限值/合同失败。一次发送前SSH连接中断发生在只读preflight，0生产root/PID/call；同一合同和Run身份恢复后仅启动一次生产。

独立NumPy nativeQ4在5阶段及final核能量、Ru、UV/H1及raw/active；保存节点力与独立回放最大差2.663e-17，FEMd精确、原边界最大差7.35e-18。独立CPU直接读取完整实际Phi复核所有投影，最大向量差probe1.019e-15／production1.926e-15，阈值标签不变；保存模型/隐藏与基底身份、damage输出行及最后模型/字段均一致。anchor/history没有独立保存的前后张量，相关不变性依据已审代码和worker冻结检查，不能称独立数组核验。

四幅图及侧注已实际查看，主图纵轴放大以显示小变化；降能仅0.02487%，不能从线段高度推断大改善。图与完整独立物理分析位于/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_persistphi_f72434a_20261019T112844Z_production/analysis_persisted_phi_hidden_newton。

源f72434af30f40582067bdfd3f0bd4e91924f2396，branch codex/hard5-q4-t3-2x2-20261005，Taobo GPU5，probePID902586／productionPID905803均退出。Runs pf_s04e011_persistphi_f72434a_20261019T112844Z_production及pf_s04e011_persistphi_f72434a_20261019T112844Z_probe；receipt含精确命令/log/archive/UUID。生产远端74files/888934824bytes，本地selective71files/85226856bytes逐文件大小/数量核验；3大实际Phi留计算端，非完整本地镜像。原E003/E011/PBD/各Newton与失败证据保留。最终独立数值、图与报告审查已通过。

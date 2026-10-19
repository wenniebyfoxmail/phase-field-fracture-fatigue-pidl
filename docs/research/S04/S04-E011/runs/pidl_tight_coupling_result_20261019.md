# PIDL c20 单隐藏步—Newton 输出头耦合判别（2026-10-19）

本轮在同一冻结 c20 峰值上完成8对隐藏特征更新与Newton输出头校正。新PIDL终点比上一轮PIDL终点弹性能低 **0.0119238%**，但全局位移残差高 **0.190787%**；active场误差只降 **0.0582395%**，相关性略降。头部闭合已验证，整体FEM场仍未复现。

目的：检验更频繁的头部校正能否改善此前两段隐藏优化的进步，继续区分PIDL优化不足与参数化限制。与上一轮从完全相同的`e2dc61d`网络、审计保存的实际Phi/T开始，未从上一轮最终网络继续。

做法：每完成一个隐藏优化步，立即以一致弹性切线Newton＋line-search校正UV头；最多8对。每对重置Torch L-BFGS历史，故隐藏侧没有跨步s/y拟牛顿曲率。这是校正频率、历史重置和工作分配的联合变化，不是纯频率消融，也不是在线搜索候选内重求头部的variable projection。只允许头部已闭合的完整对作为后继初态及最终解；未按FEM场误差选择终点。

固定项：c20/substep4/rawstep99，U=0.11999988，native Q4/2×2 GP，eta=0；力学计算始终使用同一FEM damage、原UV边界，B0 Smooth Boundary damage anchor和damage输出行参数不动，阈值仍为1e-10。初态直接复用实际Phi，隐藏改变后才生成并保存当前完整401列特征基，后续头部复用；各基自然rank386，无强制旧秩或ridge。共享隐藏变化可能改变未参与力学计算的NN damage输出，不能称NN damage场冻结。保留B0和约束Q4 damage路线，本轮未新增damage求解、FEM求解、历史提交或演化。

FEM参照是从原s3历史独立重启、条件收敛的c20s4 outer18，history commits=0；不是修复后整条轨迹或物理真值。表中全部场指标由同一独立NumPy Q4算子重算；UV为质量加权相对L2，active为g(d)ψ+的GP积分加权相对L2（分母为该FEM场范数，6.099倍即约609.9%）。Ru为自由节点位移残差L2。

| 方法／状态 | 弹性能 | Ru | UV相对L2 | H1相对误差 | active相对L2 | active相关性 |
|---|---:|---:|---:|---:|---:|---:|
| 条件收敛FEM outer18 | 0.004320576025 | 3.776e-15 | 0 | 0 | 0 | 1 |
| PIDL共同初态 | 0.005268400005 | 0.01348894 | 7.54865% | 0.5876389 | 6.120899 | 0.1025180 |
| 上一轮PIDL两block终点 | 0.005267089573 | 0.01352165 | 7.53965% | 0.5871243 | 6.102823 | 0.1027320 |
| 本轮PIDL最后闭合head8 | 0.005266461534 | 0.01354745 | 7.53491% | 0.5868483 | 6.099269 | 0.1027257 |

本轮PIDL的active积分为0.005263969499，上一轮为0.005264594916，FEM为0.004317519850；本轮raw ψ+相对L2为0.7184551（上一轮0.7187437），相关性0.8330570（上一轮0.8327238）。降低积分或能量本身不代表空间热点正确。本轮弹性能仍高于此条件FEM **21.8926%**。

梯度分别看：本轮实际Phi投影头部g∞=3.9319147e-11，8个闭合头均≤1e-10；raw UV参数g∞=4.1833941e-14；raw隐藏参数g∞=0.02465044，上一轮0.02588867。三类梯度与物理Ru坐标不同，不能相互替代；不同当前Phi基的∞范数也不作共同坐标收敛速率比较。隐藏梯度仍非零，所以既不能说全网络已驻定，也不能据此证明固定架构容量已到上限。

预注册主判据：上一轮终点E减本轮最后闭合E=6.2803892e-7>1e-10，且实际隐藏变化与8/8耦合闭合成立。因此只支持本预算内该联合策略的小幅定向降能。相对共同初态降能0.0367943%；更改场指标不能替代主判据。全局Ru略增和active相关性略降被保留，不作整体场提升结论。阶段记录显示8个闭合头的能量逐次降低，但active相对L2在head4已为6.083574，随后回升到head8的6.099269；隐藏梯度也非单调。继续降低弹性能没有保证局部场误差单调降低；最终仍使用最后闭合head8，未挑选active最小点。

成本：probe36/40 calls、6.489/60s，三次零更新Phi向量/场完全一致；production316/325 calls、114.927/540s，8个真实隐藏步（32隐藏调用）、16次稠密组装/求解、80显式切线乘积；总352/365 calls。上一轮production156 calls、66.839s，实际24个隐藏步、80隐藏调用、2次头校正。本轮更费总调用，不能称等成本排名或效率提高；未用剩余预算追加运行。此前227次专属续算调用记录保留，不把它与全部项目成本混淆。

溯源：source `137cb031bad7c5f656d08c642e65627bcdd6076c`，branch `codex/hard5-q4-t3-2x2-20261005`；Taobo GPUServer8 GPU5，UUID `GPU-5622bd47-1050-3003-246d-3cabe2b4791b`。probe PID964660；production PID971629，2026-10-19T12:38:30Z启动，正常退出。Run `pf_s04e011_tightcouple_137cb03_20261019T122720Z_production`。命令、日志、archive与输入hash在[compact结果](pidl_tight_coupling_result_20261019/result.json)及[本地launch receipt](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_tightcouple_137cb03_20261019T122720Z_production/launch_receipt.json)；remote root `/mnt/data2/drtao/wennie/pf_s04e011_tightcouple_137cb03_20261019T122720Z_production`，archive `/mnt/data2/drtao/pidl_archives/pf_s04e011_tightcouple_137cb03_20261019T122720Z_production`。CUDA_VISIBLE_DEVICES/PIDL_ARCHIVE_DIR/TMPDIR/XDG_CACHE_HOME均按已审执行器指定。

取回：remote213files/2,669,365,121bytes，本地选择186files/96,042,119bytes，逐路径/大小核验；9份大Phi和18份模型仍在remote，未宣称完整本地镜像。独立CPU只读核验完整实际Phi投影、weights/当前基绑定、后继起点、head8最终身份、固定FEMd/原边界与damage输出参数；各头GPU/CPU标签一致。23隐藏张量改变；17阶段保存的force与独立Q4最大差3.067e-17；Phi投影CPU/GPU最大差1.673e-15。没有新forward/SVD/求解。代码27个小测试通过。源实际Phi与输入文件hash见compact source清单及独立审查JSON。

传输事件：production首次代码包SCP在启动前超时；只读核验没有claim/PID/输出/计算后，从本轮probe复用相同SHA已验证包、保留partial，并原样恢复contract/输入；staged_not_launched=0calls，然后单次原执行器启动。不是求解重试或版本变更，独立回执复核通过。

图：[完整四图与sidecar](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_tightcouple_137cb03_20261019T122720Z_production/analysis_tight_coupling/README_analysis.md)；所有图已实际检查。主阶段图有放大能量轴，视觉降幅不能替代上面0.0119%的量级。See：隐藏候选为橙色空心点，闭合头为蓝点，头部重复达标而物理Ru没有持续下降。Therefore：加强这种耦合可以再降一点能量，但不足以消除FEM热点差异；本纯神经分支下一步应优先判断隐藏更新对物理残差/热点的有效方向与预条件，而非继续把已闭合头部阈值收紧。此建议未执行新试验，也不覆盖另一对话的D6整体混合设计。

最终独立字段／图／报告复核：通过；数值、四张实际图、sidecar及限定结论均已核验，无阻断问题。

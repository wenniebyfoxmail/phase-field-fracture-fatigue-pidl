# 后续方向对照：45度混合加载（计划，未执行）

目的：在同一初裂、材料和无疲劳静态问题下，检查 FEM/PIDL 的一致性是否随载荷方向变化。先完成已授权0度24态轨迹；45度为后续独立算例，不加入本次R011/R010。

## 角度定义与边界

论文式(29)记载荷角为ω；当前代码变量theta表示同一从x轴量起的顶边位移方向。采用同一幅值U，顶边 ux=U cos(theta), uy=U sin(theta)，底边两分量0，两侧自然边界。0度为水平剪切加载，90度为竖直拉伸加载，45度为两分量相等的混合加载。U=.4时45度各分量约.2828427；若各分量都设.4，实际幅值变为.5656854，不能作为等幅方向对照。

保留几何[-.5,.5]^2、初裂[-.5,0]×{0}、平面应变AT1/AMOR、E1/nu.3/Gc.01/ell.01/eta0，原24个幅值载荷及各自FEM/NN论文罚项和初始化。不能把旧参数不同的拉伸结果直接充作90度对照。

## 必要实施与验证

- FEM同时设置ux_increment=deltaU*cos(theta)、uy_increment=deltaU*sin(theta)，核对实际顶边两分量。保留整个原生PF、力学算法和接受规则。
- PIDL通用边界分支支持任意theta；当前exact_bc仅支持竖直，45度沿用本静态剪切使用的通用分支。训练输入、网格、网络和优化保持，FEM场不作监督。
- 验证器必须按角度核对两分量边界；投影反力 R_parallel=Rx*cos(theta)+Ry*sin(theta)，同时保留Rx,Ry及横向反力，能量与幅值U对应。不能只用水平反力代表45度载荷反力。
- 逐U、同一post_solve_pre_history_update状态比较位移、相场、裂缝转向、弹性/裂缝能与反力；相同支撑映射规则，另外保留各自原网格结果。

## 科学判断与预算

先运行一个45度完整配对，从初态重新计算；不做角度网格扫描。它能区分仅0度配置/边界偶合的问题与随混合模式改变的优化和损伤演化差异。单条synthetic轨迹不建立道路或跨材料泛化结论。

本次仅设计，没有45度RunID、远程部署或训练。待0度实际成本与误差可用后，给出45度完整计算预算；目前不能承诺在原窗口内额外启动。若0度FEM仍提前失败，先用保存原生组装/返回点解释该瓶颈，避免把未合格求解器复制到新方向。


## 2026-10-21 人方执行授权与准备审核

人方明确批准0度同点返回修复及FEM/PIDL比较后，继续相同幅值45度，不逐项询问。原00:20Z截止、累计3hFEM/6GPUh及资源上限覆盖两方向，不新增窗口。45度准备代码独立只读审查通过：theta tensor显式float32匹配x.dtype；launcher强制参考angle45、幅值U身份；FEM顶边同时施加dispX/dispY并核验两分量和投影反力。0度配对尚未完成，45度仍未启动；部署控制器尚待绑定预算/顺序审查。

- `run_manav_static_fem_angle.m` SHA256 `92e15f53cc12ee194e7c4e814e35abe0df3d51f5f4a89639ced266d7f4e70ed2`
- `run_manav_static_pidl_angle.py` SHA256 `5639cf07a5119117b02d0a878d1705f7455d9e0ec404ee0551ad1b300aaa290a`
- `launch_manav_static_pidl_angle.py` SHA256 `7366b3133223834ffc707ef9829af8b1bf495107719a9db2117ece1ec2e2b6c0`
- `verify_manav_static_reference_angle.py` SHA256 `f71e031f9de3685b76605cbef31c59dd9ce5406cc8b546dd1f5556c2e5264404`


45度部署候选：FEMR013、NNR014，尚未创建producer/root。两端控制器要求0度R012/R010配对summary的FEM完整、NN完整正常退出、24共同态、角度0；45NN另绑定R013的45/U完整FEM引用。FEM从原3h扣已知进程wall与全部旧操作秒数（可能重叠，保守重复计）；NN从原6GPUh扣0度NN实测wall及环境检查。以0度实测成本的1.25倍估计新方向，预算/截止不足以完整比较则不启动碎片；这只是工程资源估计，不保证45度相同速度。原CPU/RSS/CUDA/目录限制与固定host/UUID均保留。新控制器审查待收口，科学代码审核不替代控制器审核。


45度部署控制器最终只读准备审查通过，详见本地angle_deployment_review.json：最终发送cap取prepared/fresh更小值并更新config/base64/hash；FEM exact-child前按预留NN/收尾后的固定deadline再clamp并检查正剩余时间；NN exact-child前重新核对1.25倍0度实测时间预算；旧ledger解析错误、非有限/负费用或PID不一致均停止。没有创建45度producer目录或启动计算。
- `execute_manav_static_fem_angle.py` SHA256 `d1e69f1ef30dedd5c395eafaa36f19a6bfc5047eb40cc9672e76f96b4df6c985`
- `execute_manav_static_pidl_angle.py` SHA256 `b111ae0666169a67d038a11b9364396128b03b285e77349f89986f8d143b1d9f`
- `supervise_manav_static_angle.ps1` SHA256 `0ed15086d3ef8b3af9251fa450bed02487027bd3d60d116adb9c0ed60d8de499`
- `supervise_manav_pidl_angle.ps1` SHA256 `1c9a1217a750af4d72bfc75d2953c2598adca9a8cdc94c76de24c12a35af406a`

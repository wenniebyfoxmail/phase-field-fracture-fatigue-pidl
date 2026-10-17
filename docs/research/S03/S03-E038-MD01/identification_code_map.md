# 当前 identification 代码在哪里

当前使用的工作树：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp/`。
不要把项目根目录或其他聊天的同名脚本当作本次执行版本。

## v1主实现：E037，保持不动

[`scripts/md01_frame_geometry.py`](../../../../scripts/md01_frame_geometry.py)
是本次青色候选／骨架／橙色主路径的主实现，无训练权重或分割网络：

| 函数 | 输入→输出 | 主要原理 |
|---|---|---|
| `read_frame()` | 既存原件＋固定ROI→原生RGB裁剪 | 字节／SHA／方向／尺寸核验 |
| `extract()` | RGB＋粗引导＋排除多边形→mask／excluded／safe | 灰度≤100、101px局部背景对比≥20、引导60px邻域，12px接触及30行连通范围过滤 |
| `metrics()` | mask＋safe→骨架、几何指标、有序路径／厚度 | `skeletonize`、候选面积、2×EDT局部厚度，边界附近缺失保留 |
| `dominant_paths()` | 骨架→每片段代表性主路径 | 像素图、测地距离与两次最远点搜索；不是全部分叉网络或真实裂尖 |

配置：[`E037/frame_support_lock.json`](../S03-E037-MD01/frame_support_lock.json)
保存逐帧粗引导和遮挡排除区域；[`E037/source_lock.json`](../S03-E037-MD01/source_lock.json)
保存来源、ROI和旧结果保护。粗引导是观察者提供，不是自动全图检测，也不是真值标注。

v1来源图：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E036-MD01/raw_images/`。
本轮只用IMG_0375／0379／0385／0388／0391.JPG，对应18／19／21／22／23。
v1既有掩膜／路径／指标在E037-R001和R002的`stepN/`目录，不覆盖、不回写。

## E038稳定性检查：独立新入口

[`scripts/md01_geometry_stability.py`](../../../../scripts/md01_geometry_stability.py)
只新增预定OAT扰动，不改v1源文件。`extract_variant()`只改变灰度上限、局部
对比阈值、粗引导x/y平移；继续调用v1的几何定义。运行默认设置须逐像素／
逐路径／逐指标复现已有v1，否则停止，不将偏差当作新结果。

- `self-test`：纯合成默认一致性／排除／空值／OAT规则检查，不读真实图片。
- `prepare`：生成源件及旧结果哈希清单，不解码图片；旧预测只哈希保护、不解析。
- `run --manifest <R000/input_manifest.json> --output <fresh_run_directory>`：
  对5图×9设置保存新结果，不测预测误差、不选择新最优参数。

解释与参数范围见[experiment.md](experiment.md)。本轮已准备的清单：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E038-MD01/runs/S03-E038-MD01-R000/input_manifest.json`。
执行需使用新的输出目录；不要覆盖旧Run，`run`也会拒绝覆盖。

[`scripts/plot_md01_geometry_stability.py`](../../../../scripts/plot_md01_geometry_stability.py)
仅读取保存的数组、路径和指标，生成原图／掩膜／骨架／主路径／沿线厚度及
所有扰动的对照；不重测、不调参。展示骨架的3×3加粗仅为可读性，不进入计算。

## 与旧半深度分开

[`scripts/d01_crack_profile_diagnostic.py`](../../../../scripts/d01_crack_profile_diagnostic.py)
仍是旧半深度剖面算子，本轮不修改／运行其测量或重算旧分。
E037／E038的2×EDT是候选掩膜的像素厚度代理量，不是半深度、物理开口或毫米宽度。

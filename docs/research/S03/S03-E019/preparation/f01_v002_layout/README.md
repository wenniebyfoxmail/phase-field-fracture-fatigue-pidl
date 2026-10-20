# F01 V002-L01 布局入口 — 本机只读显示验收通过

## 当前结果（2026-10-20）

经人方HQ新一次限定授权，复用已过V1，原独立者完成SHA-only初查、两张
原SVG实际完整目视及原V3，52.154秒／零SVDQR／无新阻断，结论仅为本机
显示REVIEW_PASS。两行重叠消除，右完整色标／底注／J_Q原值标签可见，
初末七SHA与HEAD一致。见[新一次独立收据](../../font_svg_v002_l01_remaining_visual_r002.md)。
旧keyNotFound首停、旧时间及未做V3记录保持，见[首次验收](../../font_svg_v002_l01_evidence_review.md)。
本次无重绘／重算／科学数组／留出读取，科学与真实反演仍未认证。
此前G一次生成七件的事实保持，见[G运行记录](../../font_svg_v002_l01_g_results.md)。

## 准备版本（生成前快照，2026-10-20）

完整入口、来源与输出白名单、拒覆盖／布局映射、生成与只读验收精确命令
已补齐，见 **[最终执行包](execution_package.md)**。继续同一 owner／D3。
代码快照 `a8b10844c173f6d7f7479251685e78137fdc5f80`；[生产及只读 CLI](layout_release.py)、
[来源清单](source_manifest.json)、[人工测试](test_layout_release.py) 已另存。

24 项纯合成 XML／内存测试一次 exit0、无警告、零 SVD/QR，未重复旧测试。
测试只证明人工布局变换与内存保护分支；未对真实 SVG 运行脚本、生成或
渲染候选、继续真实图形验收。右侧色标／完整画面和最终身份仍待完成。
实际生成／验收停在人方具体决定前，不改原 renderer、V001/S01 或冻结产物。

下方为**历史草案原文**，保留当时“未测试／没有生产 CLI”的事实，不是当前
入口状态；其中旧 `layout_draft.py --check-only` 和四 SVG 核对命令已由最终
执行包取代，**不得与新版七件收据格式混用或据此执行**。

## 历史：最小布局补丁草案（当时未执行）

2026-10-20。当前唯一动作是本地准备：静态读取既有验收记录、SVG文本及
原图器源码，新增本准备目录两文件。不改原源码、V001/S01或其他冻结产物，
不导入/编译/测试草案，不重绘、渲染、续验或读取科学数组。

## 目标与复用

目标仍是DIC到可验证状态反演。本草案只解决F01显示可读性，owner仍为本
聊天S03-E019-D03-F01、D3，不另建科学实验。原结构和S01说明已通过的范围
保留；原首停及未完成范围不追改。见 ../../font_svg_s01_remaining_evidence_review.md。
已搜索S03-E019协议/scripts及research_hq/F01归档文件名，未找到同等完整
布局草案；不复制其他任务的科学内容，不重做先前结构或数值测试。

## 已定位的原因（非重新数值实验）

1. 原图器`residual_svg`的行距245；y说明为`top+218`、下一行标题为
   `top-18`。实际冻结SVG的第一行说明y=368/font12、第二行V标题y=377/font16。
   这两个基线只隔9个SVG单位，与独立者1224×783初始视图中发现的重叠一致。
   它是布局带相交，不需要读取/重算残差或修改原数据。
2. 冻结账本SVG中三个蓝矩形的height均为字符串
   `0.029214469610109317`，data-value均为`3.3796289660782525e-10`。
   原图器使用`300*(J_Q/ceiling)`的线性高度；不必重算这个式子即可直接看到
   保存的高度小于1个SVG单位。难辨是已有线性比例的显示限制，不是J_Q为零。
   本轮只读取这些SVG属性和源码，未重新计算比值、柱高或科学量。

## 具体补丁与前后参数

草案代码：[layout_draft.py](layout_draft.py)。它只定义已有SVG树的布局变换；
没有写文件/生成模式，CLI仅有未来`--check-only`，当前未运行。原图器不改。

准备起点HEAD：`99467e6a80d45af24d016a4c0098c7aa8fb408a3`。
草案代码SHA256：`3e566dc3e1100c4dcd523fd5d70cafe86242d0d24b030cacc64c37f825ccc4e9`。
原图器SHA仍为`625e312c760a9f1685fe9afd4aaeea0cadcf772556eab87999a27e5bec4bdf99`；
两原SVG的SHA与旧独立检查相同（草案代码也固定），本轮只是新的静态定位
来源核对，不补签旧验收尚未完成的最终身份核验。

| 对象 | V001 | 拟另存V002-L01 | 明确保留 |
|---|---|---|---|
| 残差画布 | 1460×730 | 1460×820 | 宽度、点/色值/坐标属性与色标内容 |
| 第二行整体 | 原位置，标题y377 | 加一个`translate(0 70)`布局组，标题显示y447 | 每个点原cx/cy/data-mm/data-x-mm/data-y-mm、fill/r不变；只是整组屏幕平移 |
| 第一行y说明 | y368 | y368不动，至V标题间距变为79 | 原文字、单位、字体不变 |
| 残差底注 | y695（可选零范围说明y665） | y785（可选说明y755） | 原文不改、S01术语解释继续有效 |
| 账本画布 | 1020×660 | 1020×720 | 原所有柱/黑点/轴几何、data-value和线性尺度不动 |
| J_Q可读性 | 约0.029单位的蓝带 | 三条蓝色文字标签y585/607/629，直接复制原SVG data-value字符串；y660说明未放大柱高 | 无最小柱高、无乘数、无log轴、无新统计量或重新舍入 |
| 账本底注 | y620 | y690 | 原文、未接纳限制不变 |

标签不是把蓝带人为加粗或声明数值已验证。第二行整体平移不在物理空间
重新配准/插值，色标RGB也不重新生成。原metadata保持来源身份，不把V001
源receipt伪称V002执行收据；未来另存运行须独立记录来源及布局派生映射。

计划另存目录（当前不创建）：

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V002-L01
```

本草案没有生产CLI。未来生成包必须另经人方审批，独占新目录/新文件，并
同时明确新图同名说明、V001/S01来源引用和新布局映射收据；不能盲复制S01
中`Same-directory derived_receipt.json`到新目录造成错误引用。所有V001/S01
原件保留，原renderer、计算、容差、预测不变。当前不生成SVG或说明/收据。

## 后续仅排版验收命令草案（当前不执行）

须先另批新派生版本生成，并取得实际产物身份；以下不是本轮的执行许可，
不是完整已审生产包。工作目录为本worktree。独立者先静态核对草案及SHA，
有问题停止，不修改后自行重试。原结构/S01通过范围只在来源身份相同时继承。

1. 只读检查（单线程、60秒软预算、标准库）：只读V001两SVG和已另存V002-L01
   两SVG，核原SHA与拟定的确切布局变化；不读数组、不重渲染。CLI不调用
   原renderer，不写文件，不导入NumPy/SciPy/Matplotlib，不做SVD/QR。

   启动前必须先核草案SHA与上面固定值一致，再核实际clean HEAD和获批版本；
   输出SHA若不匹配立即停，不执行下一条：

```bash
shasum -a 256 docs/research/S03/S03-E019/preparation/f01_v002_layout/layout_draft.py
git status --porcelain
git rev-parse HEAD
```

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -I -S -B -W error docs/research/S03/S03-E019/preparation/f01_v002_layout/layout_draft.py --check-only
```

   比较对象是SVG布局树，不是数据重算或图像像素渲染；允许的变化只有上表。
   脚本内构造参考XML树仅用于字节/属性差异核对，不输出新图。缺少未来产物
   会停止，不自动生成或改路径。现在没有运行本命令，也不声称脚本已通过。
2. 只读检查exit0且无异常后才由独立者打开已生成的新图各一次，实际UI目视；
   不能以树匹配代替看到完整图：

```bash
/usr/bin/open -a Safari /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V002-L01/residuals.svg /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V002-L01/square_ledger.svg
```

   必须核两行无重叠、三条J_Q原值标签清楚且蓝带未被夸大、底注无裁切，
   并**补完先前未审的残差图右侧完整色标/整幅范围**。记录视图与缩放，
   不保存截图或导出新图。未见区域不能签通过；工具不可见就报告，不换渠道。
3. 目视无阻断后，核开始/结束HEAD和clean、四SVG字节身份；这是原来未完成
   的末次身份检查，不因本次静态准备而视为已补齐：

```bash
git status --porcelain
git rev-parse HEAD
shasum -a 256 /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001/residuals.svg /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001/square_ledger.svg /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V002-L01/residuals.svg /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V002-L01/square_ledger.svg
```

   最终实际生成包还需把其新说明/映射收据及V001/S01十件保留身份加入明确
   白名单，沿用既有验收；本草案的四SVG命令不冒充完整冻结十件/新映射验收。
   这些元数据检查也须在生成时保存起始值，不能拿旧回传冒充新末检。

首个非预期异常、警告、文件变化、预算/权限错误或视觉阻断立即停止，不
重试/续跑/自动修补。不改阈值；不读B003数值/真实数组/新数据/留出，不启动
C/D，不外发。旧布局失败、右侧色标未审完及末检缺失始终保留；当前不重验。

## 交付状态

只完成最小可审阅代码草案、前后参数和未来命令，未运行Python/语法检查/
测试/渲染/验收。草案未独立代码审查，不宣称Code Ready或视觉问题已修复。
下一次审批可以面对这一具体布局方案，而非再次只收到“建议修图”；实际
生成、独立验收和任何新科学工作仍需要明确授权。

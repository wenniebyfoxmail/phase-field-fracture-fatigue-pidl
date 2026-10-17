# 2026-10-17：两帧四区域源图核对材料

状态：核对材料已准备，用户首轮回答已原样保存并完成对应关系公开；
局部诊断，不是像素真值或性能验收。不是实验重跑，不修改v1。
本次限定来源为已曝光Step18／IMG_0375.JPG和Step19／IMG_0379.JPG。
不读其他阶段原图，不读取预测误差，不联网、不联系人员、不启动agent；
不修改仓库代码或共享Obsidian／Roadmap。

## 固定定位方法

仅加载E038 R001这两帧已保存v1、contrast_minus5、contrast_plus5的mask，
以及原excluded和safe；不提取、重建骨架／路径、测厚、配准、预测或评分。
先验证R000来源清单及其对这两帧原图的字节数／SHA，再验证六份npz与
E038独立审核所记录的输出身份。若未提供具体输出hash，记录当前hash，
不把事后记录冒充执行前冻结；遇到明确不符则停止。

范围=原ROI[3800,900,4800,3500]内、~excluded且safe。
每帧两类差集：(contrast_minus5.mask & ~v1.mask)与
(v1.mask & ~contrast_plus5.mask)，各自与固定范围相交。
8邻域分量按像素数降序，平局按分量最上方像素、同一行最左方像素的
坐标字典序；全候选排序与定位保存。选择第一名，不按外观挑样。
中心为分量内距像素坐标均值最近的像素；距离并列按y、x升序。
无分量留空，不换帧。新增／消失若空间重叠保留并记重叠像素数。

每区裁出同中心原生256×256细节、512×512上下文，分别保留无标记原图
和仅有中性定位点的版本。偶数裁框为[cx-size/2,cx+size/2)、y同。
不得增强、锐化、插值放大；ROI外留白，不用外部内容补齐。
一次性随机打乱为A–D，中性编号无阈值／来源线索；对应表另存。

## 首轮核对说明

默认核对者为用户。此前已看过相关算法图，不称完全盲核；本轮仅隐藏
具体来源／增删条件与算法图层。不由S03或其他AI补写用户标签。

- C：可见裂缝候选。上下文中有可追踪的狭长裂纹样走势和延续依据，
  不能明显归为孔洞、文字、边缘、胶或装置；仅属图像判断。
- N：可辨非裂缝结构。有正面可见依据归为孔洞、纹理、标记、装置、
  胶或边界；不能只因“不够细长”就选N。
- U：不确定／混合／遮挡。分辨率、对比、遮挡或混合结构不足以区分，
  或定位点指向不清；允许四块全U。

每卡仅填写分类、可见依据、不确定性，不测宽、不画精确边界、不猜算法。
首轮不显示阈值／增删身份、mask／骨架／主路径、任何面积或厚度变化、
预测值／基线误差／收益／参数推荐。不能计算四块准确率或推断总体性能。

## 保存与解盲

本地材料目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E038-MD01/source_review_materials_20261017_v1/`。
reviewer/仅含中性卡片、原生裁图、分类说明和空白表；sealed/保存来源、
完整定位／候选排序、卡号对应表与输出身份，不在首轮界面展示。

收到分类时先逐字保存用户回答和时间，再公开对应；原标签不回改，
解盲后补充另列。新增C只提示可能补细裂，新增N只提示可能引伪支；
消失C提示可能损细裂，消失N提示v1可能有伪结构；U不推荐阈值优劣。
之后再做“可见依据—算法增删—可能修复”对照，仅提出一项最小掩膜
片段保留／排除建议或明确证据不足，不实施，不改骨架和主路径。

当前不提出修复方向；先等用户源图分类，不因这四块整体换阈值。

## 已完成的材料整理

4／4规则选区存在，未替换帧或按外观重选。两原图、六份保存npz与
来源清单／既有独立审核记录共10项身份一致；保存前后hash相符。
各类所有连通片段的面积、定位锚点、边框、排序以及选中片段全部像素
坐标、均值与最终原图坐标均已保存，未改原始支持。新增／消失的差集
像素交集为0；原生裁框若相交，保留并在overlap_records.json逐项记录。

- [首轮入口：中性A–D卡与说明](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E038-MD01/source_review_materials_20261017_v1/reviewer/START_HERE.md)
- [空白分类表](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E038-MD01/source_review_materials_20261017_v1/reviewer/分类表.md)
- 管理记录（首轮不展示）：sealed/selection_records.json、
  candidate_component_order.csv、card_source_condition_mapping.json、
  overlap_records.json、四份difference_locator.npz、creation_receipt.json、
  final_material_integrity.json，均在上述本地材料目录。

图像共4张1088×944拼版卡及16张原生裁图（4卡×2尺寸×原图／定位点），
每图同名说明文件。逐像素确认原图裁图拷贝、尺寸与ROI外白色留空；
四张卡实际打开检查排版，没有填写C／N／U。首轮文字不含来源文件名、
阶段号、阈值数值或增删身份；真实对应关系另存，不在首轮页面链接。
没有模型／算法实验或测试重跑、代码修改、新agent、联网或跨聊天消息；
共享Obsidian／Roadmap未修改。v1、旧半深度、旧评分和既有扰动结果不变。

下一步只接收用户分类，先保存原始回答和时间再解盲。源图依据—算法
增删—修复方向对照表尚未生成，最小修复建议待分类证据，不预先实施。

## 2026-10-17首轮回答与解盲（上述待分类文字为历史记录）

用户回答A／B／C／D均能看见裂缝；原始文字及记录时间已先保存，之后
才读取对应表，未回改四个C标签。用户逐卡依据／不确定性没有展开，
保留为“卡片中有可见裂缝”，不外推到每个算法差集像素均是真裂缝。

- [解盲前原始回答](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E038-MD01/source_review_materials_20261017_v1/responses/20261017T210258Z_first_round_user.md)
- [四卡来源坐标—增删身份—局部解释及唯一修复提案](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E038-MD01/source_review_materials_20261017_v1/responses/20261017_first_round_debrief.md)

A／B是15相对20新增（19／18），C／D是20提高到25后消失（19／18）。
不计算四卡准确率，不据此选择15或25。用户另指出噪声误检与紫色过覆盖；
代码确认紫色是人工粗排除，含~excluded硬屏蔽，不能当作裂缝预测。
只提议先收紧Step19装置／胶的粗排除边界，释放被误盖的可见混凝土，
真实遮挡仍未知；未实施，未改代码／mask／骨架／主路径／旧评分。
原始reviewer空白表及首轮材料保留，不用解盲意见回填改写。
本轮未修改共享Obsidian／Roadmap，未发跨聊天消息或启动agent。

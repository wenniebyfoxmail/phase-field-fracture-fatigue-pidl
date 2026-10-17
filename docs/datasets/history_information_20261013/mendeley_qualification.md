# Mendeley裂长标签与位移资格审计

> 后续范围更正：本文保留2026-10-13抽样审计的实际边界。2026-10-17用户另行授权后，完整原始位移和插值包已经下载并作探索性测量，见../../research/S02/S02-E006/mendeley_full_data_report.md。新增候选未升级为可靠物理真值，原预测负结果不变。

2026-10-13；source DOI10.17632/dywwnjv22h.1；C1数据能力审计，未训练、拟合或预测评分。

## 关键修正

**官方文字说4个裂长试件，但实际工作簿四张sheet仅对应两个试件编码。不能把四张sheet当作四个独立试样。** 17,925个CSV文件/19个位移组的库存也不等于19条完整有标签的预测轨迹。

本次取得官方文件清单、完整43,064B XLSX和6个选择性CSV。工作簿SHA256与发布值完全匹配：`366be8711993ec0100c1830ca5f57d70ded3855bd12ced818ceec7f0f1c9b053`。
位移RAR总长5,814,691,113B，未全量下载：通过RAR5官方格式读取CRC校验的Quick Open缓存headers；取得17,925个CSV成员的名称/偏移，再按固定stage选择6个原始member，验证实际header与缓存一致、uncompressed size和data CRC。完整RAR SHA256未验证，不冒充完整数据镜像或全成员CRC验收。

## 四sheet的实查

| sheet | 试件编码候选 | 标签行数 | Figure ID范围 | 单sheet相邻cycle gap |
|---|---|---:|---|---|
| E_0_175_1(Section 5.1) | E_0Deg_17.5%_#1 |42|1121–2281|300/1200|
| E_0_175_1(Section 6.1) | 同上 |38|1305–2285|600/1200|
| C_15_20_1(Section 5.2) | C_15Deg_20%_#1 |41|621–1421|300/600/1200|
| C_15_20_1(Section 6.2) | 同上 |35|750–1430|600|

156/156行满足README `N=30*(Figure ID−1)`，ID严格递增且Ground Truth列有限。对应原始RAR缓存manifest均找到唯一同stage文件。原始CSV命名中的17.5%对应sheet编码175；C/E及角度一致。
两同编码sheet无精确重复Figure ID，但cycle覆盖重叠，不能当独立重复试件。合并后E80个、C76个唯一stage标签；E没有相邻30cycle标签对，C有10对跨sheet的候选相邻标签。后者须先确认两个sheet的label定义与测量方法一致，不能默许拼接。

## 资格结果

| 项目 | 结果 | 依据/限制 |
|---|---|---|
| 30cycle索引 | 算术与命名一致 | README与所有标签行一致；实际machine-cycle/采集日志未取得。不能因索引公式正确就认证同步相位 |
| 位移与标签stage对应 | manifest级156/156；6样例payload核验 | CSV头stage1121/1122/1305/621/622/750匹配选定文件编号；四sheet各首标签stage均包含在样例中。非全156payload读取 |
| 连续位移库存 | 两组完整ID范围 | E1184帧1102–2285，C829帧602–1430；各无重复/范围内缺号。原始header cache的完整库存不等于每帧字段/测量质量全部验收 |
| 相位/参考 | 未资格化 | 样例字段只有id,x,y,z,displacement_x/y/z；无force、load phase、timestamp数值或reference-stage。文件夹仅名义load比例；不能当作同相位响应 |
| 坐标/节点连接 | mm单位明确，固定参考未证 | 六样例7列、18,568–18,687nodes，坐标/位移均有限；相邻stage节点数不同。不能按row直接差分，也不能假定重编号id对应同一材料点 |
| 独立性 | 仅两个元数据编码，不是四 | 未取得匿名physical specimen serial/批次/重复号与两sheet谱系说明；两个条件变化也与试样混杂 |
| 裂长参考/误差 | 未建立 | 官方明确裂长从PT场测得；同DIC链输入与标签相关。XLSX“Ground Truth”是作者列名，不证明独立物理真值；“Predicted”列不能作为输入、参考或测量误差 |
| 标签单位/几何定义 | 待确认 | CSV长度单位mm；XLSX裂长列未标单位。须确认裂长单位、edge从何处量、central是一侧长度/双侧总长/其他定义，不能用坐标mm自行补全标签定义 |
| 30cycle未来裂长 | 不合格为密集多试样benchmark | 无单sheet30cycle目标对；跨sheet仅C有10候选。禁止由未来标签插值创建30cycle真值 |

## 本次证据与曝光

本地raw root：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/open_data/mendeley_four_specimen_audit_20261013/`。
文件：`files_metadata.json`、`archive_header_manifest.json`、`selected_member_receipt.json`、`audit_receipt.json`、XLSX与6个CSV。
源https://data.mendeley.com/datasets/dywwnjv22h/1，CC BY4.0；官方README已读取；论文只有publisher preview，不以preview声称核读完整实验方法/误差讨论。
选定6帧是四sheet首标签与两相邻stage，不是按模型表现挑选。工作簿标签和这6帧均已development-exposed；未查看作者PT模型、未执行pickle或torch.load、未训练、未评估作者预测误差。其余CSV只有headers/names被审计，不能称作全量内容已验收。

## 最小补充问题

1. 四sheet是否实际来自两个相同物理试件的不同预测实验？官方“four specimens”与两编码差异如何解释？提供匿名serial/谱系即可。
2. 确认CSV stage↔Figure ID↔machine cycles、采样load phase、DIC初始参考、x/y/z是变形还是参考坐标、节点id是否稳定。
3. 提供156标签的直接来源与单位/投影定义、PT↔CSV↔label变换；尤其确认两同编码sheet是否同一测量流程与坐标参考。
4. 是否有已有裂长重复提取或独立相机/显微测量的误差资料？没有时请明确说明；不请求新实验或整包模型。

不自动发送作者邮件。本轮结论`CONDITIONAL_STAGE_JOIN__NO_GO_FOUR_SPECIMEN_OR_DENSE_30CYCLE_CRACKLABEL_BENCHMARK`，不是预测性能负结果。

## 等待FATACRACK回复期间的可做工作

当前可做确定性数据挖掘：库存与缺测图、phase/reference清单、谱系/重复检测、同坐标节点连接检查、固定ROI响应特征的算术验证、target可用跨度与purged split生成、从future泄漏到输入的审计。不要把模型预测残差、曲线平滑残差或像素尺寸当作物理测量误差。

可以设计但本轮不执行的训练：

- **FATACRACK发布标签预测sandbox**：另行明确降级claim为“在两条development记录上预测未来发布的DIC-x”，可选固定ridge M0/M1；校准物理误差不是这种纯标签描述任务的逻辑前提。相位定义已明确，但同源标签噪声、记录独立性、训练/评估时间边界必须承认。新协议须显式另定范围、冻结并审核/授权，不能绕过当前“物理资格满足后才执行”的承诺。
- **Mendeley测量场surrogate**：只有phase/reference/稳定空间连接确认后，才可另行测试30cycle位移场预测。其结果是仪器场预测，不是裂长预测或道路支持。
- **Mendeley稀疏标签sandbox**：若同试件sheet谱系/目标定义确认，可考虑直接可观察的600或1200cycle等跨度；按发布真实标签连接，不插值制造30cycletruth。仅两条件记录仍不足跨试样泛化，不能称四试件。

目前不建议：FPRM式90%缺失演示（两组标签太少且并非完整目标真值），相场参数/损伤反演，大模型/architecture sweep，使用作者Predicted列训练，模拟物理不确定性校准，以及道路部署/RUL结论。不得重开LTPP/DCB旧失败协议。

本轮训练数0。Dr Réthoré的回复是FATACRACK物理资格的补证途径，并非所有纯工具/数据探索工作的前置条件。

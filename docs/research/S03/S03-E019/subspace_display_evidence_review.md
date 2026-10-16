# E019-D01-R001-V01 — 独立只读显示验收暂停记录

2026-10-16；独立本地Codex：/root/e018_code_review。
用户批准确切B一次及独立只读显示验收。下文保留完整独立回复；不修改
新渲染收据、源report或任何原冻结产物，不把部分检查写成完整通过。

## 完整独立回复

已立即停止，不出具 PASS_DISPLAY；未补查、修复、重绘或修改文件。

截至停止时，独立完成：

- 确认开始 HEAD 为 clean `6c46d3767931e71742093e58b5a1ff6465aae6b4`。
- 固定report SHA、四项源码／方案身份、受审快照、五项产物哈希与新收据匹配。
- `plot_values.json` 与源report允许字段直接一致：C1精确0及通过状态、C2/C3保存比值和预登记负控状态均保持；原阈值未变，未访问evidence。
- 核对收据五项线程均1、预算60秒、`rendered`；8.305492792045698秒仍是成功收据写前取样。
- 独立复核保存的23个布局检查对象：画布安全边距、数值标注位置与指定重叠条件满足。
- **亲自查看实际PNG**：纵轴标签完整，标题／副标题与数值标注分离，C1零点圆标完整，阈值线1可读；未发现此前两项布局问题。

暂停原因：

主代理现报告，经其读取本机Matplotlib源码确认，字体缓存初始化提示来自 **logging WARNING**，并纠正此前“不是warning”的说明。此发现不是我的独立源码核查；但原方案要求任何新警告停止，不能事后自动豁免。它也解释了为何 `-W error` 未必将其转换为Python警告异常。

尚未完成：

- 实际同名说明完整读取及官方sidecar检查；
- PDF文件头／EOF／pdfinfo完整性检查；**没有PDF目视验收**；
- 验收结束后的再次哈希及结束HEAD核对。停止后未补查。

本轮已核对的新收据SHA为：
`6b33a047d06453b079022825582ae04fce165ab8ad9580c6b2deb46b60f040c8`。

渲染成功记录和上述已完成检查保留，但不构成完整显示验收，更不涉及D01数值或真实E019根因通过。若继续，应先由用户明确批准如何处理这条已存logging WARNING及剩余只读验收；不自动重绘或重试。

## 主代理补充：事实与分类纠正

终端实际输出（不在图器render.log中，保留在本记录）：

```text
Matplotlib is building the font cache; this may take a moment.
```

主代理在收到此提示时误视为普通初始化信息；B已exit0并生成图，独立验收
启动后，主代理只读本机
`/Users/wenxiaofang/miniconda3/lib/python3.12/site-packages/matplotlib/font_manager.py:1039`
核实：源码注释为Delay the warning by5s，threading.Timer(5, lambda:
_log.warning(...))发出上述消息。因此它是logging WARNING，不是被
Python -Werror捕获的warnings.warn异常。核实后立即通知独立验收停止，
没有再补做sidecar/PDF/结束哈希或重绘检查。先前给审查者“非warning”的
说明撤回，以本条纠正为准；不改既有receipt或把该消息从运行历史删除。

这条消息的代码触发条件是新字体缓存构建超过5秒，不是计算Q、求解、
数据损坏或布局失败的证据。新缓存本来已在方案中声明，但原停止规则
没有单列这条日志的例外，本轮不自行豁免。原数值阈值/失败/负控状态不变。

后续最小动作候选：经用户明确批准，仅将此确切已存字体缓存日志归为
预期初始化消息，继续剩余只读说明/官方sidecar/PDF完整性/结束哈希验收。
无需再次执行B、重新出图、重算或SVD；任何其他新异常仍停止。当前未执行。

## 2026-10-16：获批仅该确切缓存日志分类后，续验完成

用户本次明确批准，将上述确切字体缓存logging WARNING作为预期初始化
保留，只继续V01剩余独立只读验收。其他新异常仍立即停止，不自动重试。
没有更改原方案/代码/图/数值/receipt，不把历史暂停记录删除或追改。

### 完整独立续验回复

PASS_DISPLAY，限定 **S03-E019-D01-R001-V01 显示派生物**。无剩余必须修改项；不代表D01数值验收或真实E019根因通过。

#### 完成范围

承接上轮独立检查：

- 固定report白名单字段与 `plot_values.json` 完全一致，原值、角色、状态及阈值不变。
- 四项源码／方案身份、五项产物哈希、单线程／60秒记录及23个布局对象核对通过。
- 已亲自查看实际PNG：纵轴标签完整，顶部标注无重叠，精确零点圆标完整，判据线1清晰。本轮未重复绘图或数值检查。

本轮补完：

- 完整读取同名说明；来源、公式、颜色、单面板、负控及解释限制符合项目模板。
- 官方sidecar检查通过：**2个图文件、1个说明，错误为零**。
- PDF文件头、EOF及 `pdfinfo` 正常：单页、691.2×388.8 pt、未加密。**未渲染或目视PDF，PNG目视不能替代PDF视觉检查。**
  :codex-file-citation{path="/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D01/S03-E019-D01-R001-V01/q_identity_ratio.pdf" purpose="source"}
- 固定源report、全部五项新产物、收据、四项源码／方案及审批文本末次哈希均与先前记录一致。

#### 警告、预算和边界

确切字体缓存提示仍保留为 **logging WARNING**；仅因用户本次明确批准，作为预期初始化处理，不改称“非警告”，也不豁免其他警告。本轮无其他新警告或异常。

原收据的 **8.305492792045698秒**是写成功收据前取样，不是全部最终化完成后的精确耗时；后续写后检查成功退出的记录保留。本轮验收时间不写回原预算。

未导入图器／producer，未重绘、重算、QR／SVD／求解或运行测试，未访问evidence、真实数组或留出，未修改文件或外发。

开始／结束 HEAD 均为 clean：
`00a76c3c311d77da07acaaafcaf21d5b7e92aa84`

#### 最终字节身份

```text
source report  f6276a7d474cde6675d99649d8256027edea16902e7c259af2fab24c3535a689
receipt        6b33a047d06453b079022825582ae04fce165ab8ad9580c6b2deb46b60f040c8
PNG            93856e2492c7857cb4e728bf6d7bfc0777dc06c4f9a20da6b63517f12872735b
PDF            37e0ffcee9103daab2a10a11ffedea74bc55afd54b14cc8536c9a69301f70a57
sidecar        6e5b0cefa313935ab6e05e383f89f8fe0a04d96e1b685c72855acf776ea86af3
plot_values    a13205daa803661703fcbf507cddcca86a94496ea34c4bdb5b47555a3a926bfc
render.log     e613d0b90495a072d30aa70ee43c832c41d7bd31bc483e2392356ca0d2d5048b
view script    d461104300d0046fa561ae390038eff8390c14310edcbec8e349395cb269458e
tests          a77c39d078cd5984a763f2766c6527662bee120da7df4f989befcafffb47b619
test design    4b4001ebe1d7ab81cfe9e9d225d4e02170a896a6512e2530ede6709652713285
display plan   fa0a408e2b78c54b1160b83b4ece5cad91d698550e671f55fc5f9eea984737bb
approval       8a9fd4ea099a88726ea6122faeba341bd6bb0e981bc6303f7746a2256d79fcff
```

V01显示验收到此完成。D01未完成的独立算术验收及真实E019原失败／暂停状态均不改变，不自动继续。

### 主代理接收

只采纳上述显示验收结论。项目记录可更新为V01显示完成；原数值账本验收
仍单列待完成，不自动打开真实数组/留出或续跑诊断。冻结产物全部保持。

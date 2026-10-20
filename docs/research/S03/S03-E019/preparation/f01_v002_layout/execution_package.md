# F01 V002-L01 完整离线布局执行包

2026-10-20，Europe/London。沿原 S03-E019-D03-F01 owner／D3，继续同一
离线布局准备步骤，不另建科学实验。**三模式入口已备，24 项合成 XML／
内存测试一次通过；本轮未对真实 SVG 运行脚本、生成／渲染候选图或续验。**

目的仍是可验证的 DIC 状态反演；本次只补显示可解释性，不改变或认证
科学数值。这里一次列全生成与剩余验收入口，实际执行等待针对本版本、
目录及命令的具体人方决定，不再为每个准备小项增设实验或测试阶梯。

## 1. 固定版本与复用

| 项目 | 身份 |
|---|---|
| 代码＋人工夹具＋清单快照 | `a8b10844c173f6d7f7479251685e78137fdc5f80` |
| [layout_release.py](layout_release.py) | `fda7a06e4ced32db18b592ff9b0a9c6249c9e6091f1f77d690a0c34e1944141c` |
| [test_layout_release.py](test_layout_release.py) | `3d3dbefbc6fb7ffe6f3cb289ecb4a56bf748a998a0d703b56b22d04942f964f4` |
| [source_manifest.json](source_manifest.json) | `2b19ff62464aa7759e982cd084ed54cc7809aff2026fa144ca2b6c17d80f5b75` |
| 原 [layout_draft.py](layout_draft.py)，保持、不运行 | `3e566dc3e1100c4dcd523fd5d70cafe86242d0d24b030cacc64c37f825ccc4e9` |
| 原 `scripts/aa2024_saved_svg.py`，保持、不导入 | `625e312c760a9f1685fe9afd4aaeea0cadcf772556eab87999a27e5bec4bdf99` |
| 原 `scripts/aa2024_runtime_guard.py`，保持 | `e7bf15a9a46fa60dcc1ef41cbd3f86c2d41fb44bcda6de1ba9300df8cd76874c` |

以上除 commit 外均为 SHA256。沿用原草案的复用搜索，不重启 D1；旧 README
草案保留在 Git `c1bf2f71d7900c07b008550e2daff9dd8610132e`。本轮必要静态
差异核对合并完成，不扩展独立审查。原已通过范围与首停记录保持，参见
[独立验收记录](../../font_svg_s01_remaining_evidence_review.md)；它不是新版
图形的通过结论。本轮也不冒称取得新的独立代码／图形审查结论。

## 2. 精确来源与输出白名单

唯一允许的派生来源目录（OLD）：

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001
```

未来生成／只读核对只读取该目录十件：

```text
residuals.svg
residuals.md
square_ledger.svg
square_ledger.md
runtime_guard_events.log
derived_receipt.json
derived_completion.json
residuals.sidecar_s01.md
square_ledger.sidecar_s01.md
sidecar_mapping_s01.receipt.json
```

十个精确 SHA 逐项列在固定 `source_manifest.json`，取自既有 S01 独立验收
记录，**不是本轮重开来源后取得**。生产时必须再核十件完全相同，目录多件、
少件或任何 SHA 不符即停。原同名说明只参与身份核对；新说明采用 S01
companion 的语义。读取保存 SVG 属性不等于重开 B003 数值文件，后者仍禁止。

唯一拟新建目录（NEW；本轮不创建，也未声明已核其实际新鲜性）：

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V002-L01
```

只允许新增七件，OLD 无任何新增、替换或追加：

| 新文件 | 来源／用途 |
|---|---|
| `residuals.svg` | OLD 原 SVG 的布局派生，不重画数值场 |
| `residuals.md` | OLD `residuals.sidecar_s01.md`＋布局说明和来源引用修订 |
| `square_ledger.svg` | OLD 原 SVG 的布局派生，柱高／点／保存值不变 |
| `square_ledger.md` | OLD `square_ledger.sidecar_s01.md`＋布局说明和来源引用修订 |
| `runtime_guard_events.log` | G01 独占创建；成功时为空 |
| `layout_receipt.json` | 运行身份、来源十 SHA、代码五 SHA、映射及四件输出／事件文件 SHA |
| `layout_completion.json` | 绑定 layout receipt SHA；不是图形或数值验收通过标记 |

入口还只读自身、测试、原草案、原图器、G01 五件代码及清单，并执行必要
Git 元数据检查。执行标准库和固定 G01 字节；不导入原图器、NumPy、SciPy、
Matplotlib，不调用字体管理器、网络或求解器。Git／Python 自身运行时读取
不称科学输入；不承诺全进程所有系统调用只访问上述七／十件。

## 3. 唯一允许的布局变化与映射

| 对象 | V001 → V002-L01 | 保持 |
|---|---|---|
| 残差画布／背景 | 1460×730 → 1460×820 | 宽度、第一行、色标内容／范围／单位 |
| V 行 | 四框、28 文字、2592 圆点合入 `translate(0 70)` 组 | 圆点 `cx/cy/r/fill/data-*` 原字符串；非物理坐标配准或空间插值 |
| 残差底注 | y695 → y785；可选说明 y665 → y755 | 原文、科学值 |
| 账本画布／背景 | 1020×660 → 1020×720 | 原柱／黑点／轴、线性比例、保存值 |
| 三条蓝色标签 | y585／607／629，逐字复制各臂原 `data-value` | 不重算、不改舍入、不设最小柱高、不改 log 轴／乘数 |
| 账本说明／底注 | 新 y660 说明柱高未放大；原底注 y620 → y690 | 蓝带不解释为零；未接纳限制不变 |

保留原 SVG metadata 来源身份，另加布局派生 metadata，不把原 V001 run／
renderer 当成新运行。新说明保留 S01 对 RGB 色标插值／空间插值的区分、
原数值文本和限制；只插入布局说明及替换 Related assets 引用，继承的
provenance 块明确标为来源，不冒充 V002 执行记录。

`layout_receipt.json.mapping` 每图记录 OLD SVG 路径／SHA、OLD S01 companion
路径／SHA、NEW SVG 路径／SHA、NEW 同名说明路径／SHA。新说明引用 NEW
layout receipt／completion，并用 OLD **绝对路径**引用旧 derived receipt 和
S01 映射，不能留下错误的“同目录 derived_receipt.json”。B003 来源路径仅
作为继承文本，不触发文件读取。数值与柱高不变，也不重新生成色标。

## 4. 保护、预算与停止

- 起止核 CLI、清单、五件代码；Git clean、代码快照为祖先，后继只能是
  docs；即使 Python 在 docs 下，其 SHA 仍固定，不能替换已测试字节。
- 生成在读取 OLD 前检查 NEW 不存在，写前再查；拒符号链接／非目录祖先。
  独占 mkdir，独占建文件并读回，既有目标绝不覆盖。实际新鲜性到获批时核。
- OLD 十件读取前后、写入后／完成前均核 stat 和字节／SHA；核新七件的
  精确成员、映射、收据和 completion 绑定。任何额外文件亦停止。
- 六线程变量均 1、CUDA 空、`-I -S -B -W error`。生成 G 单次 **60 秒软预算**；
  验收 V1–V3 为同一 **60 秒软观察窗口**，独立者连续计时，不把脚本各自
  的 60 秒兜底相加。Python 内含启动／I/O／Git／打印前后检查；不承诺硬实时
  抢占。外部非零退出、超时或首停优先于已写标记，不补签成功。
- 生产入口显式安装未改 G01；标准日志 WARNING 及以上、标准 Thread 未
  处理异常立即停。无字体日志豁免、缓存预热或事后成功解释。既有 G01 的
  native／恶意修改／非原子限制保持；本轮不重测其历史用例。
- 首个非预期异常／警告、身份差异、预算到限或视觉阻断即停。不重试／
  自动修补／续跑／换路径／清理半成品／另开 RunID。失败 NEW 留作部分产物，
  即使已有 completion 也不能称完成；处理它须新指示。
- 人工测试不覆盖真实文件系统／Git／G01 全链路；防护无敌对并发或全局
  原子保证。未来仍以退出状态、首尾身份、实际显示和独立记录共同判断。

## 5. 一次人工验证与合并静态差异核对

2026-10-20，tool chunk `46ea82`，同步 exit0，无运行中 session／警告：
**24/24，一次通过，未重试**。unittest 主体 `0.004 s` 不含全部导入；整条
命令通过打印前后软预算检查 <60 s，未记录更精确的全程时长。stdout：

```json
{"status":"ARTIFICIAL_XML_MEMORY_ONLY_24_PASS_NOT_VISUAL_QA","actual_svd":0,"actual_qr":0}
```

磁盘输入仅两件代码；安装 audit hook 后仅允许这两件只读，并拒绝文件写入、
子进程、网络或建目录等。SVG、说明及文件碰撞均用人工 XML／字节串／BytesIO；
未读真实 SVG、report、B003、真实数组或留出。测试时 HEAD 为 `c1bf2f71...`，
新代码未提交；上方快照随后收录**相同 SHA 字节**，不伪称测试发生在后来
的 clean commit。清单在测试后准备，实际来源核对未执行。

24 项覆盖：残差画布、V 组、点属性、来源不变、色标不变、底注、点数／
画布拒绝；柱高／点不变、literal 标签、账本画布底注、缺 J_Q 拒绝；保留
metadata、说明原科学文本及正确来源、缺段拒绝；危险 XML 拒绝、映射；
内存独占写、已有目标拒绝、竞争不重试、读回不符、60 秒边界、错误路径拒绝、
JSON 完成绑定／重复键拒绝。没有重复原 F01 40 项或 G01 历史测试。

必要静态差异已合并核对：新变换沿用原草案 +70／画布／底注／literal 标签
规则，仅添加人工点数参数、安全 XML、正确同名说明引用、独占生产、映射／
身份及只读入口。原图器、G01、草案三 SHA 与上方一致；未改科学值、阈值、
柱高或冻结产物。本轮是本地主代理静态核对，不冒称新版独立审查结论；
旧 `--check-only` 不执行，不能与新收据格式混用。

以下为**已执行命令存档，不是再运行请求**：

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -I -S -B -W error docs/research/S03/S03-E019/preparation/f01_v002_layout/test_layout_release.py --code-sha fda7a06e4ced32db18b592ff9b0a9c6249c9e6091f1f77d690a0c34e1944141c --test-sha 3d3dbefbc6fb7ffe6f3cb289ecb4a56bf748a998a0d703b56b22d04942f964f4
```

## 6. 待审批生成命令 G（未执行）

后续全部命令的工作目录固定为：

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013
```

G 自带代码、Git、新目录预检；缺来源／目录不新鲜／身份不符即停，不改找
别处。只读取上述十件派生来源，不读 B003／真实／留出：

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -I -S -B -W error docs/research/S03/S03-E019/preparation/f01_v002_layout/layout_release.py --mode generate --manifest-sha 2b19ff62464aa7759e982cd084ed54cc7809aff2026fa144ca2b6c17d80f5b75 --self-sha fda7a06e4ced32db18b592ff9b0a9c6249c9e6091f1f77d690a0c34e1944141c --snapshot a8b10844c173f6d7f7479251685e78137fdc5f80
```

仅 exit0、无警告、首尾身份／空事件通过，才能记录
`LAYOUT_GENERATED_NOT_ACCEPTED`。人方可以只批准 G，或同时批准下列独立
验收；本文件本身不授予执行权限，也不自动启动 V1–V3。

## 7. 待审批独立只读验收 V1 → 目视 → V3（均未执行）

复用既有独立只读 Codex 角色。V1／V3 只读 OLD 十件、NEW 七件和固定代码／
清单，在内存构造预期布局字节作允许差异比较，不输出新 SVG、不重绘或科学
重算。原结构／S01 已通过内容在相同来源 SHA 和新映射成立时沿用；不重复
旧结构数值检查。独立者在开始 V1 前启动连续 60 秒软观察计时，到限即停。

### V1：身份、允许差异与两份新说明

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -I -S -B -W error docs/research/S03/S03-E019/preparation/f01_v002_layout/layout_release.py --mode verify --manifest-sha 2b19ff62464aa7759e982cd084ed54cc7809aff2026fa144ca2b6c17d80f5b75 --self-sha fda7a06e4ced32db18b592ff9b0a9c6249c9e6091f1f77d690a0c34e1944141c --snapshot a8b10844c173f6d7f7479251685e78137fdc5f80
```

须 exit0、无警告；两份 stdout 说明由独立者全文审阅，确认布局／来源身份
不混淆、原科学文本和 S01 区分保持、Related assets 可解析。脚本只报
`PENDING_REAL_VISUAL_QA`，不替独立者签语义／视觉通过。

### V2：上项无阻断后，打开新图各一次并实际查看

```bash
/usr/bin/open -a Safari /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V002-L01/residuals.svg /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V002-L01/square_ledger.svg
```

独立者用实际原生 UI，不以 open 成功或 XML 测试代替看到图；记录实际窗口
尺寸及可核实缩放。看完整画面、底注、残差两行标题／坐标无遮挡、**右侧
完整色标及单位／极值**；三个 J_Q 原值标签清楚且柱高未夸大。必要时在同次
打开中只读缩放／滚动并记录；首个异常／阻断立即停，不继续补查其他视角。
不保存／转换／另存截图，不改图。浏览器自然的渲染线程不称为单线程科学
计算；没有 SVD/QR 或科学库计算。

### V3：实际目视通过后，最终完整身份核对

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -I -S -B -W error docs/research/S03/S03-E019/preparation/f01_v002_layout/layout_release.py --mode finish --manifest-sha 2b19ff62464aa7759e982cd084ed54cc7809aff2026fa144ca2b6c17d80f5b75 --self-sha fda7a06e4ced32db18b592ff9b0a9c6249c9e6091f1f77d690a0c34e1944141c --snapshot a8b10844c173f6d7f7479251685e78137fdc5f80
```

独立者逐项对照 V1／V3 的 NEW 七 SHA 和 runtime_head，确认跨目视相同，
并核两条命令各自通过 OLD 十 SHA／代码／clean；receipt／completion 不替代
跨阶段比较。状态 `FINAL_IDENTITY_ONLY_NOT_VISUAL_VERDICT` 只表示最后身份。
最终人可读记录由独立者给出，不改旧收据。UI 不可见、连续窗口超时或首停
就报告未完成，不换渠道、自动重开或重置授权计时。

## 8. 当前决定边界

已备齐：生产／只读 CLI、人工测试、来源清单、精确命令、拒覆盖／布局映射
及一次测试结果；本轮未做实际输入预检、出候选图、渲染或新独立验收。
**右侧色标／完整画面及最终跨目视身份仍未完成；人工通过不关闭这些项目。**

等待人方具体决定是否允许 G 在唯一 NEW 目录生成布局版本，以及是否一并
批准 V1–V3。不因此读取 B003 数值、真实数组、stage15／新留出，不启动 C/D、
不改冻结预测／容差、不重做 SVD/QR、不外发。B003 的 incomplete／unaccepted
保持，真实 DIC 反演有效性仍是后续独立问题。

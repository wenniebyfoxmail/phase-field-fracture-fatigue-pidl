"""Emit reviewable apply_patch updates from the curated dataset records.

Original August CSV and October 6 capability audit are immutable inputs.
No raw array, model, held-out image or protected response is read.
"""
import argparse
import csv
import difflib
import io
import json
from pathlib import Path

BASE=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
HERE=Path(__file__).resolve().parent
VAULT=Path('/Users/wenxiaofang/obsidian')
RAW=BASE/'local_archive/open_data/dataset_completion_20261019'
DETAILS=json.loads((HERE/'completion_details_20261019.json').read_text())
NEXT_ACTIONS={
 'ltpp_local_six':('旧手册相关章节/本地结果核读＋本轮官方catalog', '复用标量状态和既有负结果，明确固定horizon与measurement noise的可用输入；不重开2D注册', '物理配准需新控制点/独立参考；完整机制字段尚缺', 'LTPP现有owner；本HQ仅作预测能力映射'),
 'pavetrack_pd':('已归档完整数据论文相关部分＋既有development记录', '从现有development manifest列场景状态/维修语义和可用访视，定义可比较的场景级目标', '毫米尺度与独立配准reference；不能再消费已曝光确认地点作新外测', '现有PaveTrack owner；不进入可信识别D1'),
 'mnroad':('既有官方Data/Field/Sensors说明及Cell22决定＋本轮Data页', '沿Cell22既有owner明确人工矢量定义与七状态lane/date对应，不训练', '全链身份重复性、第二section、离线raw response/数值联接', 'MnROAD Cell22 owner继续测量资格'),
 'westrack':('本轮完整官方overview；未取得数值样本或全部技术报告', '使用公开overview预写最小section/episode/survey/ESAL字段选择清单', '需实际一section表导出及QC/repair时间；门户存在尚未给raw sample', '预测HQ候选：section级标量替代路线'),
 'camhighways':('本轮官方项目说明；未宣称核读完整论文或raw sample', '把多模态空间当前状态任务与复访预测任务分开，列一小段样本需求', 'sample需团队提供；许可/CRS/标定/复访待实际文件', '静态观察或prospective base map候选'),
 'rdd2022':('原作者论文taxonomy已有审查；本轮官方API、目录、labels', '复用四类映射做box-task语义/来源兼容性判断', '像素/毫米任务需额外标签；作者/Figshare许可差异待协调', '宏观识别HQ的box对照；非当前Reliable训练集'),
 'rmdcrack':('本轮官方SSR metadata和Croissant；非payload/全文核读', '据V3模态和计数差异写最小RGB-depth-normal-cloud校验项', '须取得一组对应raw样本、单位/标定与manifest', '计量/可信识别均为静态跨模态候选'),
 'three_d_crack':('本轮官方DataPort说明/结构化metadata；无实体包', '把订阅限制、1mm采样与0.5mm标称precision写进数据适配判断', '需机构访问和样例文件/许可；full release未验证', '计量静态3D候选watchlist'),
 'contract_watchlist':('IEEE摘要与引言可读；全文与raw data未取得', '复用论文观察对象设计scene/distress ID/time/repair字段要求', '权威下载源、许可、实际manifest与完整方法', '预测HQ高频真实道路候选watchlist'),
 'zenodo_11945905':('原论文/既有P0 payload报告/其它owner结果＋本轮API', '复用342-stage和同cycle三载荷的已验收字段，继续既有owner当前文档中的有界诊断', '独立测量误差轴、多试样与固定horizon；不重读新留出响应', 'AA2024现有S03 owner；本预测HQ的误差诊断候选'),
 'crackmnist':('既有完整数据论文相关部分、HDF5审计＋本轮API/metadata', '复用S子集观测/operator诊断与现有分组清单，不新增holdout消费', 'chronology/source-frame及独立label error；当前不作时间预测', '观测/operator；不确定性→预测HQ暂不转时序'),
 'mendeley_dic_fatigue':('官方页/API/README、已归档全量审计；10-18机构全文相关章节已有核读记录，完整PDF未成功归档', '复用已验CSV/PT库存与17,895像素候选，写清当前帧测量算子、缺测和代理量含义；人工硬点仍暂停', '作者PT→length规则与少量独立光学锚点；不以它阻断一切代理量文档工作', 'S02-E006现有owner；下一决定为测量算子/独立锚点'),
 'multitemporal_concrete':('既有原论文方法章节审查＋本轮API/ZIP目录与train样本', '用已取train图/mask核对文件形式，按原始epoch/patch声明因果prefix和单slab限制', '多独立slab、load数值映射及独立reference；不能升级外资产forecast', '静态/多时相观测压力演示'),
 'nccd_pf':('既有完整descriptor、local file/semantic audit＋本轮API', '复用5388图文件/标签摘要和分类语义例外，拟窄裂缝感知压力问题', 'parent/site lineage及独立尺度；不能以分类阴性当物理无裂缝', 'Reliable HQ已审数据候选，尚未进入D1'),
 'idics_sample1':('既有选定样本qualification＋本轮ZIP目录及Challenge说明', '复用已知刚体平移/零应变作为工具负控说明，不要求加入真实断裂cohort', '科学断裂问题需要另一个真实试样/参考，不是修复此synthetic case', '工具负控owner；非裂缝增长路线'),
 'ncat_test_track':('本轮设施页及rep04-03采集方法相关内容；不是raw数值审计', '基于历史协议列section/cycle/gauge/单位/repair的最小schema需求', '一个实际section的同步survey/response/traffic/weather样本和条款', '预测HQ合作候选，先schema-first'),
 'virginia_smart_road':('本轮官方设施页；没有目标数据论文/文件', '明确需问的是是否存在长期裂缝目标和同时间信号，而非仅设施传感能力', '长期deterioration序列存在性/共享许可/raw样本', '预测HQ合作候选watchlist'),
 'prospective_cambridge_pilot':('本地设计协议及合作背景页；无采集/实测材料', '复用现有字段契约准备小型重复观测/reference可行性设计，区分同状态重复与不同时间演化', '合作许可、reference/scale可行性与独立资产/采集预算', '前瞻采集设计；不等于原计量12-specimen实验'),
}
with (HERE/'dataset_inventory.csv').open(newline='',encoding='utf-8-sig') as f:
    ORIGINAL=list(csv.DictReader(f))
with (BASE/'research_hq/identification_uncertainty_prediction_20261006/dataset_audit/dataset_audit.csv').open(newline='',encoding='utf-8-sig') as f:
    AUDIT={r['dataset_id']:r for r in csv.DictReader(f)}
assert len(ORIGINAL)==len(DETAILS)==18
assert set(DETAILS)==set(AUDIT)

def absolute(s):
    p=Path(s)
    return p if p.is_absolute() else BASE/p

def link(path,label=None):
    p=Path(path)
    assert p.exists(), str(p)
    return f'[{label or p.name}](<{p}>)'

def patch(path,text):
    old=path.read_text() if path.exists() else None
    if old==text: return ''
    if old is None:
        return f'*** Add File: {path}\n'+''.join('+'+s+'\n' for s in text.splitlines())
    diff=list(difflib.unified_diff(old.splitlines(),text.splitlines(),n=3,lineterm=''))[2:]
    return f'*** Update File: {path}\n'+''.join(('@@' if s.startswith('@@ ') else s)+'\n' for s in diff)

def payload_status(k,d):
    if k=='prospective_cambridge_pilot': return 'design_only_zero_observations'
    if k=='multitemporal_concrete': return 'bounded_public_train_rgb_mask_pair; no full archive'
    if k in ['zenodo_11945905','mendeley_dic_fatigue','nccd_pf','idics_sample1']: return 'existing_full_selected_release_or_case'
    if k in ['ltpp_local_six','pavetrack_pd','mnroad','crackmnist']: return 'existing_partial_or_product_subset'
    return 'metadata_or_sample_only; see sample receipt'

def sample_receipts(k):
    found=[]
    for name in ['sample_receipts.json','patch_sample_receipts.json']:
        p=RAW/name
        if p.exists():
            for r in json.loads(p.read_text()):
                if r['dataset_id']==k: found.append((p,r))
    return found

def current_body(row,d):
    k=row['dataset_id']; a=AUDIT[k]
    official=row['source_url']
    if k=='idics_sample1': official='https://idics.org/challenge/'
    b=[f'## 2026-10-19 统一资料复核（`{k}`）',
       '',f'**当前判断：**{d["access"]} {d["quality"]}',
       '', '| 信息 | 当前记录 |','|---|---|']
    for label,key in [('类型/用途','type'),('文件格式与体量','format'),('数量与独立单位','count'),('元数据字段','metadata'),('时间/尺度/分组','units_time'),('访问状态','access'),('许可','license')]:
        b.append(f'| {label} | {d[key].replace("|","／")} |')
    b+=['',f'[官方入口]({official})；核查日期2026-10-19（Europe/London）。',
        '', '### 本地资产和样本','',d['sample'],'']
    for s in d['local']:
        p=absolute(s)
        b.append('- '+(link(p) if p.exists() else f'历史指针 `{p}` 本轮未解析，不能标成当前可用。'))
    folder=RAW/k
    b.append('- '+link(folder,'本轮官方metadata／访问记录目录')+'；网页/结构化元数据与raw payload分别记录。')
    for receipt,r in sample_receipts(k):
        if 'error' in r:
            b.append(f'- 本轮取样请求结果：`{r["error"]}`；'+link(receipt,'实际收据')+'。已有本地资产不受该HTTP状态否定。')
        elif 'member_count' in r:
            b.append(f'- 实查ZIP目录{r["member_count"]}成员，range读取{r["range_bytes_read"]:,} bytes；'+link(receipt,'目录／样本收据')+'。目录检查不是全ZIP CRC验收。')
        for s in r.get('samples',[]):
            if s.get('file') and Path(s['file']).exists():
                b.append('- '+link(Path(s['file']),'已取样文件')+f'：源member `{s["member"]}`，{s["bytes"]:,}B，CRC检查{bool(s.get("zip_crc_checked"))}。'+(f'尺寸{s["dimensions"]}；mode {s["mode"]}。' if 'dimensions' in s else ''))
    b+=['','### 已开展的尝试与证据','',d['attempt'], '',f'本轮复用证据：{link(absolute(d["evidence"]))}。读取文档/manifest不等于重新运行其模型或复算全部历史分数。',
        '', '### 三个HQ的实际覆盖','',
        f'- 原计量／现宏观识别HQ：{d["metrology_hq"]}。',
        f'- Reliable Crack Identification HQ：{d["identification_hq"]}。',
        f'- Identification Uncertainty→Prediction HQ：2026-10-06已逐行纳入18行能力审计；当时forecasting判断为“{a["current_forecasting"]}”。这是旧快照，本轮以本节更新持有状态，不改旧试验结论。',
        '', '### 缺口与下一决定','',f'仍缺：{d["gap"]}', '',f'下一步：{d["next"]}',
        '', '来源层级：本节同时使用本轮官方页面/API与明确链接的既有本地审计；未执行新训练、预测评分、数据请求或补标注。原2026-08-27 inventory字段与2026-10-06 audit保持原样。','']
    return '\n'.join(b)

def notes(start,end):
    out=''
    for row in ORIGINAL[start:end]:
        k=row['dataset_id']; d=DETAILS[k]; p=VAULT/d['note']
        old=p.read_text() if p.exists() else f'---\ncreated: 2026-10-19\nupdated: 2026-10-19\ndataset_id: {k}\ntags: [dataset, road-crack]\n---\n\n# {p.stem}\n\n'
        marker=f'## 2026-10-19 统一资料复核（`{k}`）'
        assert marker not in old, f'already updated: {k}'
        if p.exists():
            # A prominent link points to the dated current section, preserving history.
            lines=old.splitlines(); hi=next(i for i,s in enumerate(lines) if s.startswith('# '))
            lines[hi+1:hi+1]=['',f'> 2026-10-19当前状态与完整字段见[[#{marker[3:]}]]；旧日期段落保留为历史。']
            old='\n'.join(lines)+'\n'
        out+=patch(p,old.rstrip()+'\n\n'+current_body(row,d))
    return out

def tables():
    rows=[]
    for row in ORIGINAL:
        k=row['dataset_id']; d=DETAILS[k]; a=AUDIT[k]
        rows.append({
            'dataset_id':k,'name':row['name'],'checked_date':'2026-10-19',
            'official_url':row['source_url'],'obsidian_note':str(VAULT/d['note']),
            'type':d['type'],'format':d['format'],'count_independence':d['count'],
            'metadata':d['metadata'],'access_update':d['access'],'license_update':d['license'],
            'payload_status':payload_status(k,d),'sample_status':d['sample'],
            'local_paths':' | '.join(str(absolute(p)) for p in d['local']),
            'metrology_hq_actual':d['metrology_hq'],'identification_hq_actual':d['identification_hq'],
            'uq_prediction_hq_actual':'all18 capability audit 2026-10-06; not 18 experiments',
            'prior_forecasting_capability':a['current_forecasting'],
            'reading_coverage':NEXT_ACTIONS[k][0],
            'permitted_next_preparation_now':NEXT_ACTIONS[k][1],
            'external_or_new_evidence_dependency':NEXT_ACTIONS[k][2],
            'owner_and_next_decision':NEXT_ACTIONS[k][3],
            'current_limit':d['quality'],'attempts':d['attempt'],'missing':d['gap'],
            'next_decision':d['next'],'evidence':str(absolute(d['evidence'])),
            'official_snapshot':str(RAW/k),'historical_inventory_last_verified':row['last_verified']})
    stream=io.StringIO(newline=''); writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader();writer.writerows(rows)
    out=patch(HERE/'dataset_hq_crosswalk_20261019.csv',stream.getvalue())
    md=['# 18条数据路线：HQ、Obsidian与本地资产交叉表','',
        '2026-10-19；owner为本次数据档案补全。D1复用18行原inventory与各owner最新记录。Active D2：消除“旧台账/单个HQ摘要是否代表当前资产与可推进性”的不确定性；最小动作是按同一18个ID对齐官方来源、实际持有、核读覆盖、三个HQ/科学owner、Obsidian与下一决定，纳入10-17 Mendeley全量数据。产物为本交叉表和18条笔记，不重跑科学试验。','',
        '推进条件：某条已有资产与目标相容时，交给原owner做已授权的最小准备/诊断；缺独立reference不必停掉有价值的代理量/算术工作，但不得升级物理结论。转向/回归条件：受限数据尚不可得，则仅挂起那条依赖，同时推进本地可做工作；若需改变科学问题，记录用户依据、原路线状态及新的可证伪目标。宏观识别属于10-08用户授权redirect，旧精密计量暂停。本次D2资料交付完成不等于所有路线科学资格完成。','',
        '原始目标是可信裂缝观测与未来预测。此次是文档/来源/小样本补全，不替代各路线科学目标。18/18已有2026-10-06能力筛查，本轮补11篇缺失笔记并复用7篇已有笔记；不把任何一项的文档完整度写成科学资格通过。', '',
        '## 当前必须纠正的旧汇总','',
        '- 计量HQ转向宏观识别有2026-10-08用户范围决策依据；需要修正的是标题、owner及portfolio连续性。SKill edit已安装cc2d6a5f并验证四个案例。',
        '- AA2024完整官方ZIP早已取得，但342/797状态、单试样、独立误差轴缺口仍在；其它owner同试样baseline不等于外资产UQ验证。',
        '- Mendeley完整CSV/PT于10-17已取得；17,925CSV/17,897PT帧/19组。四sheet仅两个标签编码。10-18已有测量方法核查并暂停人工硬端点，不再写“尚未持有位移”。',
        '- NCCD-PF于10-11已完整取得；原10-06 audit中的NONE local已过时。',
        '- RMDCrack官方V3公开metadata明确CC BY4.0及84.85GB；分项3214与总3200须澄清。3DCrack例包当前页面需登录/订阅。', '',
        '| inventory ID | Obsidian条目 | 本地payload | 当前缺口 / 下一决定 |','|---|---|---|---|']
    for r in rows:
        d=DETAILS[r['dataset_id']]
        md.append(f'| `{r["dataset_id"]}` | {link(VAULT/d["note"],(VAULT/d["note"]).stem) if (VAULT/d["note"]).exists() else "[["+(VAULT/d["note"]).stem+"]]"} | {r["payload_status"]} | {d["gap"]} {d["next"]} |')
    md+=['','看见什么：18条都有可追踪档案，持有范围从完整所选case/发布包到局部产品、元数据、未采设计均有。',
         '说明什么：可以按每项具体缺口安排下一步；整套预测条件尚未被任何一行自动补齐。',
         '尚不能说明：18条均可下载、均有独立测量参考、均已通过时序预测或真实道路验证。','',
         '## 来源和恢复','',
         '- 18行历史inventory及route_test_audit/report-source恢复自干净工作树codex/road-dataset-inventory-recovery-20261017提交113f5f94；主路径三文件与源比较。',
         '- 当前交叉表额外字段保存在dataset_hq_crosswalk_20261019.csv，原历史字段未被替换。',
         f'- 官方18项获取与错误收据：{link(RAW/"source_receipts.json")}；补充/样本收据在{link(RAW)}。',
         '- 查询使用agent-reach Exa，但免费接口限额；改用官方API、Jina官方网页读取和可用网页搜索。部分站点Jina403后官方直读成功。',
         '- 小样本只读取公开开发内容/目录；受保护Road420、既有确认图像、AA2024新留出响应均未访问。没有新模型实验或外联。','']
    out+=patch(HERE/'DATASET_HQ_CROSSWALK_20261019.md','\n'.join(md))
    return out

def indexes():
    index=VAULT/'01 Research Tracks/000 research note/Road crack prediction/dataset/Dataset archive index.md'
    road=VAULT/'01 Research Tracks/000 research note/Road crack prediction/0 Roadmap.md'
    title='## 2026-10-19 18行inventory完整档案索引'
    text=index.read_text(); assert title not in text
    lines=[title,'', '本节覆盖原inventory的全部18个ID；原有12篇DIC/沥青扩展候选继续保留。详细交叉表与各HQ使用状态见'+link(HERE/'DATASET_HQ_CROSSWALK_20261019.md')+'及'+link(HERE/'dataset_hq_crosswalk_20261019.csv')+'。','',
           '本轮补11篇、复用7篇既有笔记，18项各有官方入口、类型、格式/体量、metadata、样本状态、许可、既有尝试和下一决定。完整数据取得与科学资格分别记载；Mendeley已全量取得，AA2024/NCCD-PF持有状态已更新；prospective仍为0观测。','']
    for row in ORIGINAL:
        d=DETAILS[row['dataset_id']]; name=(VAULT/d['note']).stem
        lines.append(f'- `{row["dataset_id"]}` → [[{name}]] — {d["type"]}')
    lines+=['', '目的：让18行与实际档案/资产一一对应。结论：本轮文档与来源核查已完成；科学owner沿用各路线，后续D3按交叉表优先补独立reference、最小schema/sample与时间关联，不批量启动训练。','']
    out=patch(index,text.rstrip()+'\n\n'+'\n'.join(lines))
    text=road.read_text()
    original_line=next(s for s in text.splitlines() if s.startswith('- [[Dataset archive index]]'))
    new_line='- [[Dataset archive index]] — 2026-10-19：原inventory18/18已有唯一档案与HQ/资产交叉表；补11篇、复用7篇；Mendeley完整位移、AA2024及NCCD-PF持有状态已更新。下一步按各项schema、独立reference及时间缺口推进。'
    text=text.replace(original_line,new_line,1)
    additions=[]
    for row in ORIGINAL:
        name=(VAULT/DETAILS[row['dataset_id']]['note']).stem
        if f'[[{name}]]' not in text:
            additions.append(f'- [[{name}]] — 2026-10-19：已补官方入口、格式/metadata、样本与获取边界；当前缺口与下一决定见条目。')
    if additions:
        text=text.rstrip()+'\n\n### 18行inventory补全的资料入口（2026-10-19）\n\n'+'\n'.join(additions)+'\n'
    return out+patch(road,text)

def refresh_actions():
    out=''
    for row in ORIGINAL:
        k=row['dataset_id'];p=VAULT/DETAILS[k]['note'];old=p.read_text()
        assert '### 现在能做与外部依赖（2026-10-19）' not in old
        reading,now,external,owner=NEXT_ACTIONS[k]
        text=old.rstrip()+f'\n\n### 现在能做与外部依赖（2026-10-19）\n\n- 核读覆盖：{reading}。\n- 原owner／下一决定：{owner}。\n- 当前可做的准备：{now}。\n- 外部或新增证据依赖：{external}。\n'
        out+=patch(p,text)
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['notes1','notes2','notes3','tables','indexes','actions']); args=p.parse_args()
    modes={'notes1':lambda:notes(0,6),'notes2':lambda:notes(6,12),'notes3':lambda:notes(12,18),'tables':tables,'indexes':indexes,'actions':refresh_actions}
    print('*** Begin Patch\n'+modes[args.mode]()+'*** End Patch')

if __name__=='__main__': main()

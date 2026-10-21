"""Update existing owner milestone and one current roadmap line, no new log note."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
folder=Path('/Users/wenxiaofang/obsidian/01 Research Tracks/000 research note/Road crack prediction')
note=folder/'mesh对齐.md';roadmap=folder/'0 Roadmap.md'
marker='<!-- PIDL_CYCLIC_ALIGNMENT_IMPLEMENTATION_20261021 -->'
text=note.read_text()
if marker not in text:
    text+='\n\n'+marker+'\n## 2026-10-21 · 循环PIDL修复与共同设置对照\n\n'
    text+='目的：继续解释循环PIDL/FEM差距；按用户本轮指示修步内疲劳、最终残差、raw导出，再辨别优化与表达。\n'
    text+='本轮S04-E036 D2：隔离实现trial-f固定点与单次commit、fresh节点约束残差、应变直算raw；交叉审查补齐251节点硬裂纹边界及罚系数25倍差异的显式共同设置。82项人工单元/控制检查通过，默认训练路径保留。\n'
    text+='结论：实现与验证设计完成，尚无新NN/FEM收益。MATLAB/native admission与条件窗口harness未完成；拟2个完整加载卸载窗口+中期2峰值、条件优化/表达探针，上限48GPUh+8FEM墙钟h，待本轮预算批准。raw修复仅改变诊断，不产生物理轨迹收益。\n'
    text+=f'[完整方案]({ROOT}/docs/research/S04/S04-E036/experiment.md) · [本地检查]({ROOT}/docs/research/S04/S04-E036/VALIDATION.md)。该准备不改变D21/R008等其它已冻结结果、预算和重试边界。\n'
    note.write_text(text)
old=' 另：循环代码审计确认步内f耦合差异及标准raw导出错误，19态已核验；无新求解。'
new=' 另：S04-E036循环修复与共同设置对照设计已备，82项轻量检查通过；48GPUh+8FEMh提案待预算批准，无新训练/求解。'
r=roadmap.read_text();lines=r.splitlines(keepends=True)
idx=next(i for i,line in enumerate(lines) if line.startswith('- [[mesh对齐]]'))
if old in lines[idx]: lines[idx]=lines[idx].replace(old,new)
elif new not in lines[idx]: lines[idx]=lines[idx].rstrip('\n')+new+'\n'
roadmap.write_text(''.join(lines))
assert marker in note.read_text()
print('Updated existing mesh milestone and one current Roadmap entry; other owner text preserved.')

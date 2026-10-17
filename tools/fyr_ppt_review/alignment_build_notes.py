"""Fifteen-page bilingual narration PDF and all-slide Markdown."""
from pathlib import Path
import json,html
from reportlab.platypus import SimpleDocTemplate,Paragraph,Image,PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

W=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/fyr_ppt_alignment_update_20261017')
S=json.loads((W/'build/content_final.json').read_text())
pdfmetrics.registerFont(TTFont('ArialTalk','/System/Library/Fonts/Supplemental/Arial.ttf'))
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
styles={
 'title':ParagraphStyle('title',fontName='ArialTalk',fontSize=16,leading=20,textColor='#174B73',spaceAfter=8),
 'label':ParagraphStyle('label',fontName='ArialTalk',fontSize=10,leading=14,textColor='#174B73',spaceBefore=7,spaceAfter=3),
 'en':ParagraphStyle('en',fontName='ArialTalk',fontSize=11,leading=15.5,spaceAfter=7),
 'zh':ParagraphStyle('zh',fontName='STSong-Light',fontSize=11,leading=16,spaceAfter=7,wordWrap='CJK'),
 'src':ParagraphStyle('src',fontName='ArialTalk',fontSize=8,leading=11,textColor='#52616B')}
def para(t,style):return Paragraph(html.escape(t).replace('\n','<br/>'),styles[style])
labels={d['backup_original_slide']:d['backup_label'] for d in S[15:61]}
flow=[]
md=['# First-year assessment: bilingual narration\n',
    'Wennie Wan · Supervisor: Brian Sheil\n',
    '15 main slides and 55 hidden backups. B47–B55 retain the previous main slides 7–15, including their original bilingual notes.\n']
for i,d in enumerate(S,1):
    tag=f'{i:02d}' if i<=15 else d['backup_label']+f' (PPT page {i})'
    md.extend([f'\n## {tag}. {d["title"]}\n',f'![Slide {tag}]({W}/review/slides/{i:02d}.png)\n',
      '### English narration\n',d['en']+'\n','### 中文对照\n',d['zh']+'\n','Sources:\n'+d['source']+'\n'])
    if i>15:continue
    flow.extend([para(f'{i:02d}. {d["title"]}','title'),
      Image(str(W/f'review/slides/{i:02d}.png'),width=174*mm,height=97.875*mm),
      para('English narration','label'),para(d['en'],'en'),para('中文对照','zh'),para(d['zh'],'zh')])
    refs=[labels[n] for n in d['original_pages']]
    if i>=7:refs.insert(0,f'B{i+40:02d} (previous version of this slide)')
    flow.append(para('Related backups: '+', '.join(refs)+'. Sources are in the PPT notes.','src'))
    if i<15:flow.append(PageBreak())
(W/'output/Wennie_Wan_15_Main_and_Backup_Bilingual_Notes_v5.md').write_text('\n'.join(md)+'\n')
def footer(canvas,doc):
    canvas.saveState();canvas.setFont('ArialTalk',8);canvas.setFillColorRGB(.32,.38,.42)
    canvas.drawString(18*mm,12*mm,'Wennie Wan · Main talk notes')
    canvas.drawRightString(192*mm,12*mm,str(doc.page));canvas.restoreState()
doc=SimpleDocTemplate(str(W/'output/Wennie_Wan_15_Main_Bilingual_Notes_v5.pdf'),pagesize=(210*mm,297*mm),
    rightMargin=18*mm,leftMargin=18*mm,topMargin=15*mm,bottomMargin=19*mm,
    title='First-year assessment: bilingual narration',author='Wennie Wan')
doc.build(flow,onFirstPage=footer,onLaterPages=footer)
print('Wrote PDF and Markdown; English main words:',sum(len(d['en'].split()) for d in S[:15]))

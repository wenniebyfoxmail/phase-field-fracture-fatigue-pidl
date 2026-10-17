from pathlib import Path
import json,html
from reportlab.platypus import SimpleDocTemplate,Paragraph,Image,PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

W=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/fyr_ppt_15slide_revision_20261017')
S=json.loads((W/'build/content_final.json').read_text());MAIN=15
pdfmetrics.registerFont(TTFont('ArialTalk','/System/Library/Fonts/Supplemental/Arial.ttf'))
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
styles={
 'title':ParagraphStyle('title',fontName='ArialTalk',fontSize=16,leading=20,textColor='#174B73',spaceAfter=8),
 'label':ParagraphStyle('label',fontName='ArialTalk',fontSize=10,leading=14,textColor='#174B73',spaceBefore=7,spaceAfter=3),
 'en':ParagraphStyle('en',fontName='ArialTalk',fontSize=11,leading=15.5,spaceAfter=7),
 'zh':ParagraphStyle('zh',fontName='STSong-Light',fontSize=11,leading=16,spaceAfter=7,wordWrap='CJK'),
 'src':ParagraphStyle('src',fontName='ArialTalk',fontSize=8,leading=11,textColor='#52616B')}
def para(x,k):return Paragraph(html.escape(x).replace('\n','<br/>'),styles[k])
labels={d['backup_original_slide']:d['backup_label'] for d in S[MAIN:]}
flow=[];md=['# First-year assessment: 15 main slides and complete backup notes\n\nWennie Wan · Supervisor: Brian Sheil\n\nSlides 1–15 are the main talk. All 46 previous pages follow as hidden backups.\n']
for i,d in enumerate(S,1):
 tag=f'{i:02d}' if i<=MAIN else d['backup_label']+f' (PPT page {i})'
 md.extend([f'\n## {tag}. {d["title"]}\n',f'![Slide {tag}]({W}/review/final_slides/{i:02d}.png)\n','### English narration\n',d['en']+'\n','### 中文对照\n',d['zh']+'\n','Source: '+d['source']+'\n'])
 if i>MAIN:continue
 flow.append(para(f'{i:02d}. {d["title"]}','title'))
 flow.append(Image(str(W/f'review/final_slides/{i:02d}.png'),width=174*mm,height=97.875*mm))
 flow.append(para('English narration','label'));flow.append(para(d['en'],'en'))
 flow.append(para('中文对照','zh'));flow.append(para(d['zh'],'zh'))
 refs=', '.join(labels[n] for n in d['original_pages'])
 flow.append(para('Related detailed slides: '+refs+'. Full source references are in the PPT notes.','src'))
 if i<MAIN:flow.append(PageBreak())
(W/'output/Wennie_Wan_15_Main_and_Backup_Bilingual_Notes.md').write_text('\n'.join(md)+'\n')
def footer(canvas,doc):
 canvas.saveState();canvas.setFont('ArialTalk',8);canvas.setFillColorRGB(.32,.38,.42);canvas.drawString(18*mm,12*mm,'Wennie Wan · Main talk notes');canvas.drawRightString(192*mm,12*mm,str(doc.page));canvas.restoreState()
doc=SimpleDocTemplate(str(W/'output/Wennie_Wan_15_Main_Bilingual_Notes.pdf'),pagesize=(210*mm,297*mm),rightMargin=18*mm,leftMargin=18*mm,topMargin=15*mm,bottomMargin=19*mm,title='First-year assessment: 15 main slides with bilingual narration',author='Wennie Wan')
doc.build(flow,onFirstPage=footer,onLaterPages=footer)
print('Wrote 15-page main notes PDF and complete 61-slide bilingual Markdown.')

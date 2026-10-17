from pathlib import Path
import json,html,re
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
W=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/fyr_ppt_process_revision_20261017')
S=json.loads((W/'build/content_final.json').read_text())
pdfmetrics.registerFont(TTFont('ArialTask','/System/Library/Fonts/Supplemental/Arial.ttf'))
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
styles={
 'title':ParagraphStyle('title',fontName='ArialTask',fontSize=16,leading=20,textColor='#174B73',spaceAfter=8),
 'label':ParagraphStyle('label',fontName='ArialTask',fontSize=10,leading=14,textColor='#174B73',spaceBefore=7,spaceAfter=3),
 'en':ParagraphStyle('en',fontName='ArialTask',fontSize=10.5,leading=14.5,spaceAfter=6),
 'zh':ParagraphStyle('zh',fontName='STSong-Light',fontSize=10.5,leading=15,spaceAfter=6,wordWrap='CJK'),
 'src':ParagraphStyle('src',fontName='ArialTask',fontSize=7.5,leading=10,textColor='#52616B',wordWrap='CJK')}
def para(x,style):return Paragraph(html.escape(x).replace('\n','<br/>'),styles[style])
flow=[];md=['# First-year assessment: bilingual learning notes\n\nWennie Wan · Supervisor: Brian Sheil\n']
for i,d in enumerate(S,1):
 en=re.split(r'\n\s*Sources?:',d['en'])[0].strip()
 flow.append(para(f'{i:02d}. {d["title"]}','title'))
 flow.append(Image(str(W/f'review/final_slides/{i:02d}.png'),width=174*mm,height=97.875*mm))
 flow.append(para('English narration','label'));flow.append(para(en,'en'))
 flow.append(para('中文对照' if i<=22 else '中文说明','zh'));flow.append(para(d['zh'],'zh'))
 flow.append(para('Source: '+d['source'],'src'))
 if i<len(S):flow.append(PageBreak())
 md.extend([f'\n## {i:02d}. {d["title"]}\n',f'![Slide {i}]({W}/review/final_slides/{i:02d}.png)\n','### English narration\n',en+'\n','### 中文对照\n',d['zh']+'\n','Source: '+d['source']+'\n'])
(W/'output/Wennie_Wan_Bilingual_Learning_Notes_Revised.md').write_text('\n'.join(md)+'\n')
def footer(canvas,doc):
 canvas.saveState();canvas.setFont('ArialTask',8);canvas.setFillColorRGB(.32,.38,.42);canvas.drawString(18*mm,12*mm,'Wennie Wan · First-year assessment');canvas.drawRightString(192*mm,12*mm,str(doc.page));canvas.restoreState()
doc=SimpleDocTemplate(str(W/'output/Wennie_Wan_Bilingual_Learning_Notes_Revised.pdf'),pagesize=(210*mm,297*mm),rightMargin=18*mm,leftMargin=18*mm,topMargin=15*mm,bottomMargin=19*mm,title='First-year assessment: bilingual learning notes',author='Wennie Wan')
doc.build(flow,onFirstPage=footer,onLaterPages=footer)
print('Wrote 25-slide bilingual notes in PDF and Markdown.')

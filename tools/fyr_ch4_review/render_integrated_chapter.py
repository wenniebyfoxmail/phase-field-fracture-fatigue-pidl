"""Render the existing integrated chapter with local figures; no external services."""
from pathlib import Path
import re,subprocess
R=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
O=R/'local_archive/report_ch4_rewrite_integrated_20261015';D=O/'draft';V=O/'review'
s=(D/'Chapter4_Integrated_Rewrite.md').read_text()
css=V/'preview.css';css.write_text('''body{font:17px/1.65 Georgia,serif;color:#20252b;max-width:1080px;margin:45px auto;padding:0 28px}h1,h2,h3{font-family:Arial,sans-serif;line-height:1.3}h2{margin-top:2em}table{border-collapse:collapse;width:100%;font:14px/1.5 Arial,sans-serif;margin:18px 0}th,td{border-bottom:1px solid #d5dce0;padding:8px;text-align:left}th{background:#edf3f7}img{width:100%;height:auto}em{color:#3c4852}math{font-size:1.05em}''')
subprocess.run(['pandoc',str(D/'Chapter4_Integrated_Rewrite.md'),'--from=markdown+tex_math_dollars','--to=html5','--standalone','--mathml','--embed-resources','--css',str(css),'--metadata','pagetitle=Chapter 4. Results and discussion: FEM and PIDL under cyclic loading','-o',str(D/'Chapter4_Integrated_Rewrite.html')],check=True)
# Native LaTeX captions maintain chapter-based numbering; sources/figures remain local.
s=re.sub(r'^# Chapter 4\. ', '# ',s,flags=re.M)
s=re.sub(r'^(#{2,3}) 4\.\d+(?:\.\d+)? ',r'\1 ',s,flags=re.M)
s=re.sub(r'^\*Table 4\.\d+\. (.*?)\*$',r'Table: \1',s,flags=re.M)
pat=r'!\[[^\]]*\]\(([^)]+)\)\n\n\*Figure 4\.(\d+)\. (.*?)\*'
def image(m):
 path,n,cap=m.groups();n=int(n)
 wide=n in [8,9,10,11]
 start='\\clearpage\n\\begin{landscape}\n' if wide else ''
 end='\n\\end{landscape}\n\\clearpage' if wide else ''
 return start+'\\begin{figure}[H]\n\\centering\n\\includegraphics[width=\\linewidth]{'+path+'}\n\\caption{'+cap+'}\n\\label{fig:ch4_'+str(n)+'}\n\\end{figure}'+end
s=re.sub(pat,image,s,flags=re.S)
p=V/'chapter4_print.md';p.write_text(s)
header=V/'chapter4_header.tex';header.write_text(r'''\usepackage{graphicx}
\usepackage{placeins}
\usepackage{float}
\usepackage{pdflscape}
\usepackage{etoolbox}
\usepackage[font=small,labelfont=bf]{caption}
\AtBeginDocument{\setcounter{chapter}{3}}
\AtEndDocument{\FloatBarrier}
\pretocmd{\section}{\FloatBarrier}{}{}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\BeforeBeginEnvironment{longtable}{\FloatBarrier}
\AtBeginEnvironment{longtable}{\footnotesize}
\setcounter{topnumber}{3}
\setcounter{totalnumber}{5}
\renewcommand{\topfraction}{0.92}
\renewcommand{\textfraction}{0.06}
\renewcommand{\floatpagefraction}{0.7}
''')
cmd=['pandoc',str(p),'--from=markdown+tex_math_dollars','--to=latex','--top-level-division=chapter','--number-sections','--standalone','--variable','documentclass=report','--variable','fontsize=11pt','--variable','papersize=a4','--variable','geometry:margin=22mm','--include-in-header',str(header),'-o',str(V/'chapter4_preview.tex')]
subprocess.run(cmd,check=True)
# This is a multi-asset local LaTeX preview project, including the 12 external figures.
for pass_id in [1,2]:
 p=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','-output-directory',str(V),str(V/'chapter4_preview.tex')],capture_output=True,text=True)
 (V/f'latex_pass_{pass_id}.stdout').write_text(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError('Local PDF compile failed; inspect review/latex_pass_'+str(pass_id)+'.stdout')
import shutil
shutil.copy2(V/'chapter4_preview.pdf',D/'Chapter4_Integrated_Rewrite.pdf')
print('Local HTML and PDF written.')

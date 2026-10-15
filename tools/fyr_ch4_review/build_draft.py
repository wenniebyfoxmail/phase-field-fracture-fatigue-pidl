from pathlib import Path
import re,subprocess,json,hashlib,html
import markdown

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
OUT=ROOT/'local_archive/report_ch4_revision_20261015'
DRAFT=OUT/'draft';source=DRAFT/'Chapter4_Revised_Plain_English.md'
text=source.read_text()

# The browser preview stays fully local; MathJax is not loaded from a CDN.
body=markdown.markdown(text,extensions=['tables','fenced_code'])
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Chapter 4 — local English revision</title><style>body{font:17px/1.65 Georgia,serif;color:#20252b;background:#fff;max-width:1000px;margin:48px auto;padding:0 32px}h1,h2,h3{font-family:Arial,sans-serif;line-height:1.3}h1{font-size:30px}h2{margin-top:2.2em;font-size:24px}h3{font-size:19px}table{border-collapse:collapse;width:100%;font:14px/1.5 Arial,sans-serif;margin:20px 0}th,td{border-bottom:1px solid #ddd;text-align:left;padding:8px}th{background:#eef3f7}img{width:100%;height:auto}p:has(>em:only-child){font-size:15px;color:#404850}a{color:#17628a}@media print{body{margin:0;max-width:none;padding:0}h2,h3{break-after:avoid}table,img{break-inside:avoid}}</style><body>'''+body+'</body></html>'
(DRAFT/'Chapter4_Revised_Plain_English.html').write_text(page)

# Use real LaTeX captions in the printable version, with chapter numbering 4.
texmd=re.sub(r'^# Chapter 4\. ', '# ',text,flags=re.M)
texmd=re.sub(r'^(#{2,3}) 4\.\d+(?:\.\d+)? ',r'\1 ',texmd,flags=re.M)
texmd=re.sub(r'^\*Table 4\.\d+\. (.*?)\*$',r'Table: \1',texmd,flags=re.M)
pat=r'!\[[^\]]*\]\(([^)]+)\)\n\n\*Figure 4\.\d+\. (.*?)\*'
def figure(m):
    path,caption=m.groups();label='fig:c4_'+Path(path).stem
    return '\\begin{figure}[htbp]\n\\centering\n\\includegraphics[width=\\linewidth]{'+path+'}\n\\caption{'+caption+'}\n\\label{'+label+'}\n\\end{figure}'
texmd=re.sub(pat,figure,texmd,flags=re.S)
(DRAFT/'chapter4_print_source.md').write_text(texmd)
header=DRAFT/'preview_header.tex'
header.write_text('\\usepackage{graphicx}\n\\usepackage{placeins}\n\\AtBeginDocument{\\setcounter{chapter}{3}}\n\\AtEndDocument{\\FloatBarrier}\n\\setlength{\\parindent}{0pt}\n\\setlength{\\parskip}{5pt}\n')
common=['pandoc','--from','markdown+tex_math_dollars','--to','latex','--top-level-division=chapter','--number-sections',str(DRAFT/'chapter4_print_source.md')]
subprocess.run(common+['--standalone','--variable','documentclass=report','--variable','fontsize=11pt','--variable','papersize=a4','--variable','geometry:margin=22mm','--include-in-header',str(header),'-o',str(DRAFT/'Chapter4_Revised_Plain_English.tex')],check=True)
fragment=subprocess.run(common,check=True,text=True,capture_output=True).stdout
fragment=fragment.replace('\\section{Comparison setup}', '\\label{ch:diagnostic_results_discussion}\n\\label{ch:diagnostic_results}\n\\section{Comparison setup}',1)
(DRAFT/'chapter4.tex').write_text(fragment)

manifest={'task':'FYR Chapter4 local revision from existing outputs','production_pidl_commit':'ad749c8bbba8120b3961add989b11427fab86254','analysis_base_commit':'8070c028dde7c1a5ef56fb4ab21e64f9883a4c4c','overleaf_source_snapshot':'f0675a5','read_only_remote_sources':{'FEM':r'C:\Users\xw436\jobs\S04_E011_ad749c8_20261005\production_outputs\S04_E011_FEM_{Q4,T3}_C120','PIDL':'/mnt/data2/drtao/pidl_archives/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z/*_{q4,t3}_production_*'},'existing_prior_analysis':str(ROOT/'local_archive/experiments/S04-E011/runs/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z/analysis'),'new_solver_or_training_execution':False,'remote_output_mutation':False,'overleaf_modified':False,'collection_note':'The first FEM reader command failed before MATLAB started due to an escaped executable path. The corrected read-only reader completed separately. PIDL extraction completed once. All retained artifacts passed subsequent validation.','raw_artifacts':[]}
for p in sorted((OUT/'raw').glob('*')):
    if p.is_file() and p.suffix not in ['.partial']:
        manifest['raw_artifacts'].append({'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(OUT/'analysis/source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

sources={
 'initial_damage_four_arms':'New reduction of both FEM state0_analysis.mat files and both PIDL checkpoint_step_0.pt files; analysis/initial_damage_statistics.csv.',
 'initial_damage_differences':'Same recovered initial fields; analysis/initial_field_differences.csv. PIDL minus FEM on common nodes; no field clipping in metrics.',
 'unified_event_timeline':'All 120 saved peak fields per arm; analysis/all_peak_event_counts.csv and unified_events.csv.',
 'hard5_c83_damage_comparison':'Existing October paired FEM c83 peak nodal exports and current extraction of PIDL checkpoint_step_414.pt, exactly checked against earlier nodal exports.',
 'hard5_c83_active_q4':'Existing corrected native-GP c83_q4_mechanism/fields.npz in the declared paired-run analysis. Product evaluated at GP level before cell reduction.'}
for stem,description in sources.items():
    (OUT/'figures'/f'{stem}.md').write_text(f'# {stem}\n\nSource: {description}\n\nScope: synthetic, one Umax=0.12 paired Hard-5 study, seed 1. Four arms share ordered nodes; solver algorithms remain distinct.\n\nDisplay: field panels crop y to [-0.12,0.12]. Damage colours display [0,1]; raw extrema retained in tables. Signed differences use one zero-centred scale per figure. Active absolute fields use a shared log display with floor 1e-12.\n\nAllowed reading: the named existing outputs differ by the shown amounts. Event detection and field agreement are separate observations.\n\nNot established: physical truth, a unique causal explanation, or real-road prediction.\n\nCaption and reading context: ../draft/Chapter4_Revised_Plain_English.md. Analysis and source identities: ../analysis/summary.json and source_manifest.json.\n')
print('Local HTML, LaTeX, source manifest and figure sidecars written.')

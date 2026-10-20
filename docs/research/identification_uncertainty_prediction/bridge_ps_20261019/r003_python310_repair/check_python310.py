"""Actual Python3.10 compiler check. Newer ast.feature_version was insufficient."""
from pathlib import Path
import sys,json,hashlib
CODE=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/mendeley-info-value-20261019/docs/research/identification_uncertainty_prediction/bridge_ps_20261019/output_calibration_r003_completion_20261020')
HERE=Path(__file__).parent
if sys.version_info[:2]!=(3,10):raise RuntimeError('requires actual Python3.10 interpreter')
failures=[];fixed=[]
for p in sorted(CODE.glob('*.py')):
 try:compile(p.read_text(),str(p),'exec')
 except SyntaxError as exc:failures.append({'name':p.name,'line':exc.lineno,'error':str(exc)})
 candidate=HERE/'figures.py' if p.name=='figures.py' else p
 compile(candidate.read_text(),str(candidate),'exec');fixed.append(p.name)
if len(failures)!=1 or failures[0]['name']!='figures.py':raise RuntimeError('unexpected deployed compatibility failure set')
result={'actual_python':sys.version,'interpreter':sys.executable,'deployed_failures':failures,'candidate_all_python_files_compile':fixed,'candidate_figures_sha256':hashlib.sha256((HERE/'figures.py').read_bytes()).hexdigest(),'no_import_or_original_scientific_data_access':True,'newer_ast_feature_version_is_not_sufficient_for_PEP701':True}
(HERE/'actual_python310_compile.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

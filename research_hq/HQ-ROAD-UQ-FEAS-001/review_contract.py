"""Independent static audit of the frozen runner surface; never imports runner."""
import ast, json, re
from pathlib import Path

root=Path(__file__).parent;source=(root/'runner.py').read_text();tree=ast.parse(source)
protocol=json.loads((root/'frozen_protocol.json').read_text());lock=json.loads((root/'data_lock.json').read_text())
calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
strings=[n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
checks={
 'protocol_identity':protocol['experiment_id']=='HQ-ROAD-UQ-FEAS-001' and protocol['seed']==20261011,
 'single_seed_literal':source.count('SEED = int(PROTOCOL["seed"])')==1,
 'epoch_cap':protocol['max_epochs']==40 and 'range(1,41)' in source,
 'budget_cap':protocol['gpu_budget_hours']==6 and 'hard_deadline=run_start+6*3600' in source,
 'checkpoint_on_a_validation':'maximum CRACK500 A validation mean Dice only'==protocol['checkpoint_rule'] and 'score>best' in source,
 'frozen_scores':all(x in source for x in ['"U_LC"','"U_H"','"U_Z"']),
 'frozen_gate_k29':'c[28]["risk"]' in source,
 'no_network_or_subprocess':not any(isinstance(n,ast.Import) and any(a.name in {'requests','urllib','subprocess','http','ftplib'} for a in n.names) for n in ast.walk(tree)),
 'no_road420_path_argument':'road420' not in set(re.findall(r'p\.add_argument\("--([^\"]+)',source)),
 'road420_is_identity_only':source.lower().count('road420')==5 and 'Path(args.road420' not in source,
 'data_hashes_64':all(len(lock[k]['sha256'])==64 for k in ['trainzip','valzip','testzip']) and len(lock['road420_identity_sha256'])==64,
 'scope_boundary':'not physical truth' in source and 'human-review utility' in source,
}
print(json.dumps(checks,indent=2));raise SystemExit(0 if all(checks.values()) else 1)

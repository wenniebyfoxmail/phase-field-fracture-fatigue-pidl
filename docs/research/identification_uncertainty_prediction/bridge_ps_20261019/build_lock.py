"""Development tool: seal text/code/metadata only, never open scientific arrays."""
from pathlib import Path
import json,hashlib
p=Path(__file__).parent
names=['runtime_guard.py','test_runtime_guard.py','hq_authority_chain.json','state.py','contract.py','supervise.py','worker.py','analysis.py','verify.py','r002_base.py','config.producer.json','frozen_cohort.json','input_manifest.json','r002_verification.json','design.md','design_plan.json','design_source_manifest.json','interface_fixture.py','test_interface_fixture.py','test_state_contract.py']
lock={'protocol':'BRIDGE-PS-v1.0','design_commit':'569cc865a9090e050042c7daf037cd2f0e535bba','files':{n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in names}}
(p/'package_lock.json').write_text(json.dumps(lock,indent=2)+'\n');print(hashlib.sha256(json.dumps(lock,sort_keys=True,separators=(',',':')).encode()).hexdigest())

"""Read-only E022 identity/initialisation and full sampler-stream checks; no training."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'SENS_tensile'))
from aggregate_s04_e022_last_leak_screen import prepare_baseline
from s04_e022_screen import (DIRECT_LOCKS,CONTROL_LOCKS,MAP_LOCKS,build_candidate,build_relu_candidate,validate_activation,ACTIVATION_RULE,native_replay)
from run_s04_e022_last_leak_screen import make_strata,draw_stratified,PARAMETER_COUNT,RESIDUAL_PARAMETER_COUNT,predict_in_chunks
from s04_e019_frozen_residual import state_digest
from diagnose_s04_e020_features import rss


def main():
    p=argparse.ArgumentParser();p.add_argument('--old',type=Path,required=True);p.add_argument('--direct',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(2);torch.set_default_dtype(torch.float64)
    results=[]
    for state in DIRECT_LOCKS:
        d=prepare_baseline(state,a.old/'inputs'/f'{state}.npz',a.old/'backbones'/state,a.old/'runs'/CONTROL_LOCKS[state]['run_id'],a.direct/'runs'/DIRECT_LOCKS[state]['run_id'])
        g=MAP_LOCKS[state]['physical_geometry'];m=build_candidate(7,'localized',g,d['base_model'],d['coordinate_mapping']);validate_activation(m)
        uv=predict_in_chunks(m,torch.tensor(d['xy'])).numpy();np.testing.assert_allclose(uv,d['base_uv'],rtol=0,atol=0)
        original=build_relu_candidate(7,'localized',g,d['base_model'],d['coordinate_mapping']);assert state_digest(original)==state_digest(m)
        assert sum(x.numel() for x in m.parameters())==PARAMETER_COUNT
        rng=np.random.Generator(np.random.PCG64(1000010));strata=make_strata(d['damage'],d['mass']);h=hashlib.sha256()
        for step in range(10000):
            active,background=draw_stratified(rng,strata,'0.7');h.update(np.asarray(np.concatenate((active,background)),dtype='<i8').tobytes())
        assert h.hexdigest()==CONTROL_LOCKS[state]['sampler_index_sha256']==DIRECT_LOCKS[state]['sampler_index_sha256']
        formal=np.load(a.direct/'runs'/DIRECT_LOCKS[state]['run_id']/'learning_rates.npy',allow_pickle=False)
        r=dict(state=state,initial_uv_difference=float(abs(uv-d['base_uv']).max()),initial_tensor_state_equals_E021=True,activation_rule=ACTIVATION_RULE,parameters=PARAMETER_COUNT,residual_parameters=RESIDUAL_PARAMETER_COUNT,draws=10000,sampler_sha256=h.hexdigest(),E019_regions=d['paired_control']['regions'],E021_regions=d['e021_direct_control']['regions'],formal_native_vector_equals_local=bool(np.array_equal(formal,np.asarray(native_replay()))),formal_runtime_checked=False,training=False,peak_rss_bytes=rss())
        results.append(r);print(json.dumps(r),flush=True)
    (a.out/'real_admission.json').write_text(json.dumps(dict(training=False,optimizer_steps=0,states=results),indent=2)+'\n')


if __name__=='__main__':main()

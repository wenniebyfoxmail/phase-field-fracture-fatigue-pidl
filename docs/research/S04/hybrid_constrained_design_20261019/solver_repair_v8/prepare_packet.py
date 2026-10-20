"""Local code/control preparation; no arrays, network, FEM or imports of solver."""
from pathlib import Path
import hashlib,io,json,subprocess,tarfile

HERE=Path(__file__).resolve().parent
CODE=HERE.parents[4]
LOCAL=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v8_20261021')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def make_card():
    prior=json.loads((HERE.parent/'solver_repair_v6/execution_r3/execution_card.json').read_text())
    authority=json.loads((HERE/'authority.json').read_text())
    return dict(schema='hybrid-cpu-trajectory-v8',run_id='pf_hybrid_solver_v8_20261021_r5',
        run_root='/mnt/data2/drtao/wennie/pf_hybrid_solver_v8_20261021_r5',
        archive_root='/mnt/data2/drtao/pidl_archives/pf_hybrid_solver_v8_20261021_r5',
        inputs='/mnt/data2/drtao/wennie/pf_hybrid_solver_v6_20261020_r3/inputs',
        inputs_sha256=prior['inputs_sha256'],state0_id=prior['state0_id'],
        state_contract_id=prior['state_contract_id'],base_load_cycle=prior['base_load_cycle'],
        displacement_scale=prior['displacement_scale'],solver=prior['solver'],
        producer=dict(hostname='GPUServer8',account='drtao',gpu=None),
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=CODE,text=True).strip(),
        authority=authority,package_start_epoch=1792539166.,absolute_package_deadline_epoch=1792553566.,
        conservative_prelaunch_charge='Elapsed since receipt23:32:46Z; includes all preparation/review/deployment and conservative time before exact dispatch, not measured CPU.',
        old_research_known_wall_seconds=1232.4626276369672,
        prior_R4_conservative_package_charge_seconds=4390.,
        prior_R4_charge_basis="Conservative elapsed22:19:36Z through new receipt23:32:46Z; includes idle/padding, not actual CPU or producer time; covers former3689.498 snapshot and later closure without overlap with this package.",
        historical_unknown_control_reserve_seconds=600.,
        execution_enabled=True,snapshot_storage='lossless_npz_deflate1',
        snapshot_policy='Every accepted state and all D13 arrays/metadata retained byte-for-byte in uncompressed NPY members; no NN features or training. Max8GiB remote plus8GiB local retrieval.',
        retained_deps_manifest=str((HERE/'retained_deps_manifest.json').relative_to(CODE)),
        retained_deps_manifest_sha256=sha(HERE/'retained_deps_manifest.json'),
        runtime_expected={k:prior['runtime_expected'][k] for k in ['numpy','scipy','osqp','psutil']},
        budget=dict(total_envelope_seconds=14400,post_execution_reserve_seconds=600,
            cpu_wall_hours=13800/3600,cpu_cores=4,gpu_hours=0,ram_gib=32,
            address_space_gib=32,primary_gib=1,archive_gib=7,local_retrieval_gib=8,free_storage_gib_required=16,
            producer_retries=0,training_fits=0,numerical_substeps=600,replay_analysis_hours=0,
            termination_reserve_seconds=45),
        coupling=dict(**prior['coupling'],backtrack_candidates=4,schur_trigger_ratio=.9,
            schur_restart=16,schur_cycles=3,schur_action_limit=64,schur_relative_tolerance=1e-3,
            max_newton_directions=8,block_relative_tolerance=1e-3)|dict(mode='guarded_block_newton'),
        phases=[dict(id='train_A',kind='trajectory',gpu=False,wall_seconds=13800,
            cycles=120,amplitude_multiplier=.8,role='reference',initializer='previous')],
        stopping='One scientific attempt; first failure stops; no auto retry/resume or partial trajectory qualification. All100fresh evaluations and4 backtracks per direction share original300s step clock. At most8 block directions perstep, each one sparse generalLU factor/solve, separate original-scale row residuals; original mechanics/QP limits retained; no fallback.',
        interpretation='Continuous numerical feasibility only; not six-case completion, training-ready feature export, neural benefit, unique physical solution or road validation.')


def prepare():
    LOCAL.mkdir(parents=True,exist_ok=True)
    card=make_card()
    if (HERE/'execution_review.json').exists():
        frozen=json.loads((HERE/'execution_card.json').read_text())
        card['source_commit']=frozen['source_commit']
        if card!=frozen:raise RuntimeError('reviewed card is immutable; no metadata overwrite')
    else:(HERE/'execution_card.json').write_text(json.dumps(card,indent=2,ensure_ascii=False)+'\n')
    prior=json.loads((HERE.parent/'solver_repair_v6/source_manifest.json').read_text())
    paths=[p for p in prior['files'] if p.startswith('source/')]
    paths+=['source/hybrid_guarded_coupling.py','source/hybrid_reduced_tangent.py','source/hybrid_coupled_block.py',
        'tools/hybrid_producer_worker.py','tools/hybrid_deadline_guard.py','tools/run_hybrid_producer.py',
        'tools/run_hybrid_cpu_v8_budgeted.py','tools/preflight_hybrid_cpu_v8.py','tools/receive_hybrid_cpu_v8.py',
        str((HERE/'authority.json').relative_to(CODE)),str((HERE/'plan.md').relative_to(CODE)),
        str((HERE/'retained_deps_manifest.json').relative_to(CODE))]
    files={p:sha(CODE/p) for p in sorted(set(paths))}
    artifact=hashlib.sha256(json.dumps(files,sort_keys=True,allow_nan=False).encode()).hexdigest()
    package=dict(artifact_id=artifact,source_commit=card['source_commit'],files=files)
    if (HERE/'execution_review.json').exists():
        if package!=json.loads((HERE/'source_manifest.json').read_text()):
            raise RuntimeError('reviewed manifest is immutable; no metadata overwrite')
        review=json.loads((HERE/'execution_review.json').read_text())
        if review['card_sha256']!=sha(HERE/'execution_card.json') or review['artifact_id']!=artifact:
            raise RuntimeError('existing exact review differs; do not silently overwrite or deploy')
        data={name:(HERE/name).read_bytes() for name in ['execution_card.json','source_manifest.json','execution_review.json']}
        data.update({'code/'+p:(CODE/p).read_bytes() for p in files})
        buf=io.BytesIO()
        with tarfile.open(fileobj=buf,mode='w:gz') as tar:
            for name,value in data.items():
                item=tarfile.TarInfo(name);item.size=len(value);item.mtime=0;tar.addfile(item,io.BytesIO(value))
        payload=buf.getvalue()
        if len(payload)>2*2**20 or sum(map(len,data.values()))>4*2**20:raise RuntimeError('code/control bundle exceeds reviewed cap')
        (LOCAL/'code_control.tar.gz').write_bytes(payload)
        print(json.dumps(dict(artifact_id=artifact,bundle_sha256=hashlib.sha256(payload).hexdigest(),bundle_bytes=len(payload),files=len(files),root=str(LOCAL))))
    else:
        (HERE/'source_manifest.json').write_text(json.dumps(package,indent=2)+'\n')
        print(json.dumps(dict(status='prepared_awaiting_exact_review',artifact_id=artifact,files=len(files),card_sha256=sha(HERE/'execution_card.json'))))


if __name__=='__main__':prepare()

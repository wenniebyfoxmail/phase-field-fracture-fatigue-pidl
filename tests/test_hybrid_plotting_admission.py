"""Artificial dependency admission only: no producer, scientific states or fit."""
import json
import sys
from types import SimpleNamespace
import pytest
from hybrid_plotting_admission import probe_plotting
from hybrid_producer_common import write_json
from hybrid_inputs import sha256
from run_hybrid_producer import execution_specs
from test_hybrid_producer import card


def test_unknown_pin_stops_before_matplotlib_import(monkeypatch):
    import builtins
    real=builtins.__import__
    def forbidden(name,*a,**kw):
        if name.startswith('matplotlib'):raise AssertionError('unknown pin attempted import')
        return real(name,*a,**kw)
    monkeypatch.setattr(builtins,'__import__',forbidden)
    with pytest.raises(RuntimeError,match='PLOTTING_VERSION_UNCONFIRMED'):probe_plotting(None)


def test_wrong_pin_and_agg_constant_triangle_png_pdf(monkeypatch,tmp_path):
    monkeypatch.setenv('MPLCONFIGDIR',str(tmp_path/'mpl'));monkeypatch.setenv('MPLBACKEND','Agg')
    import matplotlib
    with pytest.raises(RuntimeError,match='PLOTTING_VERSION_MISMATCH'):probe_plotting('0.0.0')
    result=probe_plotting(matplotlib.__version__)
    assert result['completed'] and result['backend'].lower()=='agg'
    assert all(result['rendered_bytes'][k]>100 for k in ('png','pdf'))


def test_plot_admission_precedes_original_complete_phase_order():
    c=card()
    with pytest.raises(ValueError,match='bounded plotting'):execution_specs(c)
    c['plotting_admission']=dict(id='plotting_admission',kind='admission',gpu=False,wall_seconds=120)
    c['runtime_expected']['matplotlib']=None
    specs=execution_specs(c)
    assert specs[0]['kind']=='admission' and specs[1:]==c['phases']
    assert sum(x.get('cycles',0)*5 for x in specs)==3600


def test_first_dependency_failure_is_charged_and_stops_before_any_scientific_phase(tmp_path,monkeypatch):
    import run_hybrid_producer as r
    c=card();root=tmp_path/'run';root.mkdir();archive=tmp_path/'archive';inputs=tmp_path/'inputs';inputs.mkdir()
    write_json(inputs/'inputs.json',{})
    c.update(execution_enabled=True,run_root=str(root),archive_root=str(archive),inputs_sha256=sha256(inputs/'inputs.json'),
             plotting_admission=dict(id='plotting_admission',kind='admission',gpu=False,wall_seconds=120))
    c['runtime_expected']['matplotlib']=None
    cp=tmp_path/'card.json';write_json(cp,c);pp=tmp_path/'package.json';write_json(pp,dict(artifact_id='unit'))
    rp=tmp_path/'review.json';write_json(rp,dict(verdict='REVIEW_PASS',artifact_id='unit',card_sha256=sha256(cp)))
    monkeypatch.setattr(sys,'argv',['runner','--card',str(cp),'--package',str(pp),'--inputs',str(inputs),'--review',str(rp),'--execute'])
    monkeypatch.setattr(r,'verify_package',lambda *a:None);monkeypatch.setattr(r,'host_admission',lambda *a:{})
    monkeypatch.setattr(r.importlib,'import_module',lambda name:SimpleNamespace(__version__=c['runtime_expected'][name]))
    monkeypatch.setattr(r.resource,'getrusage',lambda *a:SimpleNamespace(ru_utime=0.,ru_stime=0.))
    calls=[]
    def failure(command,code,env,log,spec,card,runroot,archive,totals,usage):
        calls.append(spec['id']);assert env['MPLBACKEND']=='Agg' and env['MPLCONFIGDIR'].startswith(str(root))
        write_json(runroot/'plotting_admission_failure.json',dict(first_cause='PLOTTING_VERSION_UNCONFIRMED'))
        raise RuntimeError('worker exit 1')
    monkeypatch.setattr(r,'run_owned_worker',failure)
    with pytest.raises(RuntimeError,match='worker exit'):r.main()
    assert calls==['plotting_admission']
    failure=json.loads((root/'failure.json').read_text());cost=json.loads((root/'cost_ledger.json').read_text())
    phase=cost['phases']['plotting_admission']
    assert phase['completed'] is False and phase['wall_seconds']>=0 and phase['cpu_seconds']>=0
    assert cost['gpu_seconds']==0 and cost['numerical_seconds']==0 and cost['shared_analysis_seconds']>=phase['wall_seconds']
    assert failure['totals']['phases']['plotting_admission']['dependency_failure']['first_cause']=='PLOTTING_VERSION_UNCONFIRMED'
    assert json.loads((root/'terminal.json').read_text())['status']=='failed'

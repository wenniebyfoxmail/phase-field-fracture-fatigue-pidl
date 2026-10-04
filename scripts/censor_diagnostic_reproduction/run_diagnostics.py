"""Path-only orchestration of existing deterministic diagnostic scripts."""
from pathlib import Path
import importlib.util,json,os,platform,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output"
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

def main():
    OUT.mkdir(exist_ok=True)
    sys.path.insert(0,str(ROOT/"code/source"))
    import torch,numpy,scipy,h5py
    torch.set_num_threads(8)
    receipt={"started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"host":platform.node(),"platform":platform.platform(),"pid":os.getpid(),"python":sys.version,"versions":{"torch":torch.__version__,"numpy":numpy.__version__,"scipy":scipy.__version__,"h5py":h5py.__version__},"training":False,"gpu_used":False,"condor_ad_path":os.environ.get("_CONDOR_JOB_AD")}
    (OUT/"execution.json").write_text(json.dumps(receipt,indent=2))
    for envkey,name in (("_CONDOR_JOB_AD","job.ad"),("_CONDOR_MACHINE_AD","machine.ad")):
        if os.environ.get(envkey):
            (OUT/name).write_text(Path(os.environ[envkey]).read_text())
    print(json.dumps(receipt),flush=True)
    # Test only deterministic spatial/history kernels; no training loop.
    result=subprocess.run([sys.executable,"-m","pytest","-q","code/tests/test_native_q4_quadrature.py","code/tests/test_native_q4_history.py"],cwd=ROOT,capture_output=True,text=True)
    (OUT/"unit_tests.txt").write_text(result.stdout+result.stderr)
    print("unit_tests",result.returncode,flush=True)
    if result.returncode: raise RuntimeError("Kernel unit tests failed")
    for c in (76,82,83):
        dest=OUT/"operator_replay"/f"c{c}_operator_replay.json"
        result=subprocess.run([sys.executable,str(ROOT/"code/SENS_tensile/audit_native_q4_operator.py"),str(ROOT/"fem"),"--cycle",str(c),"--out",str(dest)],capture_output=True,text=True)
        (OUT/f"replay_c{c}.log").write_text(result.stdout+result.stderr)
        print("operator_replay",c,result.returncode,flush=True)
        if result.returncode: raise RuntimeError("FEM operator replay failed")
    regions=load("regions",ROOT/"run_region_energy_attribution.py")
    regions.HERE=OUT/"region";regions.HERE.mkdir(exist_ok=True)
    regions.CASE=ROOT/"case";regions.FEM=ROOT/"fem"
    regions.PIDL=ROOT/"case/archive/selected/pidl_selected_element_fields.npz"
    regions.main();print("region attribution complete",flush=True)
    gp=load("gpdiag",ROOT/"run_gp_crossswap_equilibrium.py")
    gp.CASE=ROOT/"case";gp.OUT=OUT/"gp_crossswap_equilibrium"
    gp.FULL=ROOT/"case/archive/full_selected";gp.FEM=ROOT/"fem";gp.WORKTREE=ROOT/"code"
    gp.main()
    receipt["finished_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    receipt["execution_status"]="succeeded"
    (OUT/"execution.json").write_text(json.dumps(receipt,indent=2))
    print("EXECUTION_COMPLETE",flush=True)
if __name__=="__main__":main()

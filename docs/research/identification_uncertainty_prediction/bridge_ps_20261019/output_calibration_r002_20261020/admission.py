"""Future formal admission under outer watchdog. No live preflight is done in preparation."""
from pathlib import Path
import sys,os,platform,shutil,json
import package

def admit(code,cfg,root):
 # Fail dependencies/resources before original scientific bytes or any fit.
 if sys.platform!='linux' or platform.node()!=cfg['expected_hostname']:raise RuntimeError('producer host identity')
 if platform.python_version()!=cfg['python_version']:raise RuntimeError('producer Python version')
 if len(os.sched_getaffinity(0))!=1:raise RuntimeError('one logical CPU affinity not inherited')
 if os.stat(root).st_dev!=os.stat('/mnt/data2').st_dev:raise RuntimeError('new root not on canonical mount')
 if shutil.disk_usage(root).free<2*2**30:raise RuntimeError('admission free disk below2GiB')
 mem={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')}
 if mem.get('MemAvailable',0)<2*2**30:raise RuntimeError('admission available RAM below combined2GiB envelope')
 cpus=os.cpu_count() or 1
 if os.getloadavg()[0]>=cpus:raise RuntimeError('shared CPU admission saturated')
 package.verify_dependencies(cfg)
 package.write(Path(root)/'admission_environment.json',{'hostname':platform.node(),'python':platform.python_version(),'versions':cfg['dependencies'],'available_memory_bytes':mem['MemAvailable'],'free_disk_bytes':shutil.disk_usage(root).free,'affinity':sorted(os.sched_getaffinity(0)),'one_minute_load':os.getloadavg()[0],'provenance':'actual later admission under independent watchdog; no pre-validation claimed'})

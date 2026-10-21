"""Verify the scientific interpreter and enter the runner in this same process."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import traceback

CODE = Path(__file__).resolve().parents[2]
RUN = CODE.parent
sys.path.insert(0, str(RUN/'deps'))


def main():
    expected=json.loads((RUN/'config.json').read_text())['gpu_uuid']
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == expected
    reference = json.loads((RUN/'GPU_RELEASED.json').read_text())['reference']
    assert reference['complete_valid_reference'] and reference['accepted_prefix'] == 24
    assert reference['model_contract']=='common-box-at1-seed1-20261021'
    assert reference['kkt_definition']=='normal_cone_unscaled_original_gradient_units'
    import torch
    import numpy
    import scipy
    import tqdm
    import gmshparser
    assert torch.cuda.is_available()
    assert str(torch.cuda.get_device_properties(0).uuid)==expected, 'CUDA physical GPU identity differs'
    info = dict(pid=os.getpid(), executable=sys.executable, cwd=str(Path.cwd()),
                argv=sys.argv, cuda_visible_devices=os.environ['CUDA_VISIBLE_DEVICES'], actual_gpu_uuid=str(torch.cuda.get_device_properties(0).uuid),
                device=torch.cuda.get_device_name(0), torch=torch.__version__,
                packages={})
    for m in [torch, numpy, scipy, tqdm, gmshparser]:
        p = Path(m.__file__).resolve()
        assert p.is_file()
        info['packages'][m.__name__] = dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    (RUN/'scientific_context.json').write_text(json.dumps(info, indent=2))
    print('SCIENTIFIC_CONTEXT_VERIFIED '+json.dumps(info), flush=True)
    target = CODE/'scripts/shear/run_manav_static_pidl_box.py'
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name='__main__')


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        (RUN/'scientific_exception.txt').write_text(traceback.format_exc())
        raise

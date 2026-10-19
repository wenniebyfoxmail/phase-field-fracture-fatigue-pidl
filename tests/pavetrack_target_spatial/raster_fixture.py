"""Run under bundled Pillow12.3: no real labels, images, model or torch."""
import tempfile,json,importlib.util,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,__version__
assert __version__=='12.3.0'
root=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('raster_qa',root/'scripts/pavetrack_target_spatial/run.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
with tempfile.TemporaryDirectory() as d:
    p=Path(d);inp=p/'input';out=p/'run';inp.mkdir();out.mkdir()
    scope=dict(images={'fixed':dict(image_id='fixed',location='24',width=64,height=32)},rows=[dict(index=17,image_id='fixed',location='24',context=[0,0,64,32])])
    annotation=dict(image_id='fixed',location='24',width=64,height=32,category='Transverse Crack',polygon=[[5,4],[30,4],[30,7],[5,7]])
    (inp/'annotations.json').write_text(json.dumps(dict(rows=[annotation]+[dict(image_id='other_original_training_image',polygon='must_not_access')]*849)))
    mask=Image.new('L',(64,32));ImageDraw.Draw(mask).polygon([tuple(x) for x in annotation['polygon']],fill=1)
    center,_,_=r.geom.reference(np.asarray(mask,dtype=np.uint8),[0,0,64,32])
    np.savez(inp/'legacy_center.npz',source_run=np.array('S01-E025-R001'),row_indices=np.array([17],np.int64),masks=center[None])
    try:r.load_references(inp,scope,out);raise AssertionError('barrier bypass')
    except PermissionError:pass
    (out/'prediction_freeze.json').write_text('{"all_predictions_before_reference_decode":true}')
    refs=r.load_references(inp,scope,out);assert np.array_equal(refs['center'][0],center)
    np.savez(inp/'legacy_center.npz',source_run=np.array('S01-E025-R001'),row_indices=np.array([17],np.int64),masks=np.zeros((1,32,32),np.uint8))
    try:r.load_references(inp,scope,out);raise AssertionError('legacy mismatch accepted')
    except ValueError as exc:assert 'mismatch' in str(exc)
assert 'torch' not in sys.modules
print('Pillow12.3 synthetic raster/legacy exact match, prediction barrier, unrelated-label exclusion, tamper rejection passed; no real data/model.')

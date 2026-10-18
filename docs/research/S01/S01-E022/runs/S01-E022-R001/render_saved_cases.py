"""Repair display aspect only, from the same fixed six saved case snapshots/maps."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def render(evidence, output):
    evidence=Path(evidence);output=Path(output)
    assert not output.exists(), 'fresh derived display directory required'
    receipt=json.loads((evidence/'output_receipt.json').read_text())
    cases_path=evidence/'cases.json'
    assert sha(cases_path)==receipt['files']['cases.json']
    cases=json.loads(cases_path.read_text())
    assert cases['after_prediction_freeze_and_evaluation'] and not cases['used_for_learning']
    assert 0<len(cases['cases'])<=6
    output.mkdir(parents=True)
    fig,axes=plt.subplots(6,2,figsize=(12,24),squeeze=False)
    inputs={'cases.json':sha(cases_path)}
    for pair,row in zip(axes,cases['cases']):
        path=evidence/row['snapshot']
        assert sha(path)==row['sha256']==receipt['files'][row['snapshot']]
        inputs[row['snapshot']]=row['sha256']
        with Image.open(io.BytesIO(path.read_bytes())) as image:
            assert image.size==(row['width'],row['height'])
            pixels=np.array(image.convert('RGB'))
        x1,y1,x2,y2=row['descriptor']['context']
        heat=np.asarray(row['descriptor']['heatmap']);assert heat.shape==(7,7) and np.isfinite(heat).all() and (heat>=0).all()
        vmax=max(1e-12,float(heat.max()))
        for ax in pair:
            ax.imshow(pixels)
            for box,color,style in [(b,'#51c878','--') for b in row['GT']]+[(row['original']['box_xyxy'],'#438de3','-'),(row['corrected']['box_xyxy'],'#ed6757',':')]:
                ax.add_patch(Rectangle((box[0],box[1]),box[2]-box[0],box[3]-box[1],fill=False,edgecolor=color,linestyle=style,linewidth=1.5))
        pair[1].imshow(heat,extent=(x1,x2,y2,y1),interpolation='nearest',cmap='magma',vmin=0,vmax=vmax,alpha=.6)
        for x in np.linspace(x1,x2,8):pair[1].axvline(x,color='white',linewidth=.4,alpha=.5)
        for y in np.linspace(y1,y2,8):pair[1].axhline(y,color='white',linewidth=.4,alpha=.5)
        for ax in pair:
            ax.set_xlim(x1,x2);ax.set_ylim(y2,y1)
            # Set AFTER both imshow calls; the original second call restored equal aspect.
            ax.set_aspect('auto')
        C,D=row['descriptor']['values']
        pair[0].set_title(f"site{row['location']} source{row['parent_id']} | C_sem={C:.3f}, D_sem={D:.3f}",fontsize=9)
        pair[1].set_title(f'Same context | 7x7 attribution, NOT GT | display max={vmax:.3g}',fontsize=9)
    for pair in axes[len(cases['cases']):]:
        for ax in pair:ax.axis('off')
    assert cases['kind']=='FIT_opportunity_not_selected', 'this fixed result has no OOF additions'
    fig.suptitle('S01-E022-R001 | FIT OPPORTUNITIES — NOT SELECTED; NO OOF ADDITIONS\nGreen dashed GT / blue original / red dotted correction; both panels use same context and stretched display aspect\nSaved 7x7 class attribution, NOT a crack mask; fixed score-ordered cases, per-case display scale only',fontsize=10)
    fig.tight_layout(rect=(0,0,1,.96));target=output/'F02_cases_readable.png';fig.savefig(target,dpi=130);plt.close(fig)
    report=dict(run_id='S01-E022-R001',source_commit='f8990c148b14298db16490cd6f4460794271a8dc',fixed_zip_sha256='f10e4753ba5b946cc80ac64e2a2c0d843cc5ccac4a872706915f3664ac63d32d',renderer_sha256=sha(Path(__file__)),input_files=inputs,output_sha256=sha(target),source_image_reads=0,local_saved_snapshot_display_decodes=len(cases['cases']),new_forward_rows=0,new_gradients=0,new_fits=0,new_policies=0,new_metrics=0,case_selection_unchanged=True,original_bundle_untouched=True,change='set_aspect auto after second imshow; same limits, cases, maps, boxes, no scientific recomputation')
    (output/'display_receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'README_analysis.md').write_text('''# S01-E022-R001 saved-case display correction

The original immutable ZIP and all original PNGs remain unchanged. This local derivative uses the exact same six fixed FIT opportunity snapshots and their saved7x7maps, boxes and contexts; no case selection, model forward/gradient, fitting, policy or metric recomputation. The original second imshow reset right-panel aspect to equal. Both panels now explicitly set auto AFTER all images are drawn, using identical coordinate limits. Display is stretched for readability, not physical aspect; per-case colour max is display only. The coarse map is class attribution, NOT crack GT. GT outside the fixed context is clipped. These are NOT SELECTED and there are NO OOF additions. The receipt binds inputs, renderer and output. Six local saved-snapshot display decodes are separate from the original producer's841source reads/835+6source decodes; zero additional source-image access.
''')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();render(args.evidence,args.output)

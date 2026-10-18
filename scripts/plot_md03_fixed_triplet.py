"""Exact-output visualisation of E049; never selects windows or changes masks."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image

from md03_fixed_triplet import BASE, read


def export(fig,out,stem,description):
    fig.savefig(out/(stem+'.png'),dpi=180)
    plt.close(fig)
    (out/(stem+'.md')).write_text(description)


def inspect():
    out=BASE/'R001c_native_inspection';out.mkdir(exist_ok=False)
    frames=json.loads((BASE/'R000_selection/selection_lock.json').read_text())['frames'][:2]
    fig,axs=plt.subplots(2,1,figsize=(14,9),layout='constrained')
    for ax,f in zip(axs,frames):
        rgb,info=read(f)
        ax.imshow(rgb[1550:2200,1950:3500],extent=(1950,3500,2200,1550))
        ax.set_title(f'{f["filename"]} | history only | native pixels, uint16 / 257')
        ax.set_xlabel('native image x (px)');ax.set_ylabel('native image y (px)')
    fig.suptitle('E049 history inspection | same beam interior, no enhancement / no target')
    export(fig,out,'history_beam_interior',
        '# Historical beam-interior inspection\n\nQuestion: can a crack guide be defined from histories?\n'
        'Both fixed historical TIFFs0089/0132, official hashes in R000selection.\n'
        'Two panels same native crop[1950,1550,3500,2200], code-value division257 only, no enhancement.\n'
        'Axes native image pixels, dark means original low grayscale, no algorithm overlays.\n'
        'Display does not establish crack truth, time ordering or physical aperture.\n')


def detail():
    out=BASE/'R001d_native_detail';out.mkdir(exist_ok=False)
    frames=json.loads((BASE/'R000_selection/selection_lock.json').read_text())['frames'][:2]
    for f in frames:
        rgb,_=read(f);stem=f['filename'][:-4]+'_native_detail'
        Image.fromarray(rgb[1750:2200,2450:3150]).save(out/(stem+'.png'))
        (out/(stem+'.md')).write_text('# Native history detail\n\n'
            f'Source{f["source"]}, hash{f["sha256"]}. Same crop[2450,1750,3150,2200] on both histories.\n'
            'Single native-resolution view, fixed uint16//257 decoding, no enhancement, no algorithm labels.\n'
            'Purpose: identify a source-only coarse guide before measuring or opening target.\n'
            'Dark dots are DIC speckles, not crack labels; no accuracy/width/time claims.\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('inspect','detail'))
    args=parser.parse_args()
    if args.phase=='inspect':inspect()
    else:detail()

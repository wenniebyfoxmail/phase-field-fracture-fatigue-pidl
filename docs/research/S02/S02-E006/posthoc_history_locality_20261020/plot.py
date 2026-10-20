"""Render exact saved-output diagnostics; no model execution."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'savefig.dpi': 180, 'font.family': 'DejaVu Sans'})


def plot(out):
    stage = pd.read_csv(out/'stage_summary.csv')
    reg = pd.read_csv(out/'region_summary.csv').set_index('region')
    df = pd.read_csv(out/'case_diagnostics.csv')
    fig, ax = plt.subplots(2, 2, figsize=(13, 9), gridspec_kw={'height_ratios': [1, 1.6]})
    for dx, comp, color in [(-.17, 'B_STAR', '#0072B2'), (.17, 'C_RAW', '#D55E00')]:
        values = stage['relative_reduction_'+comp+'_pct']
        ax[0, 0].bar(stage.stage_third+dx, values, .32, color=color, label=comp)
        for x, y in zip(stage.stage_third+dx, values):
            ax[0, 0].text(x, y+(.5 if y >= 0 else -1.1), f'{y:.1f}', ha='center', fontsize=9)
    ax[0, 0].set(xticks=[0, 1, 2], xticklabels=['Early', 'Middle', 'Late'],
                 ylabel='Error reduction (%)', title='A  Retained-origin thirds (not fatigue life)')
    ax[0, 0].axhline(0, color='.4', lw=.7)
    ax[0, 0].set_ylim(-3, 17)
    ax[0, 0].legend(frameon=False, fontsize=9)
    keys = ['band', 'outside_band', 'edge8', 'interior']
    for dx, comp, color in [(-.17, 'B_STAR', '#0072B2'), (.17, 'C_RAW', '#D55E00')]:
        ax[0, 1].bar(np.arange(4)+dx, reg.loc[keys, 'relative_reduction_'+comp+'_pct'], .32, color=color)
    ax[0, 1].set(xticks=np.arange(4), xticklabels=['Fixed band', 'Outside band', 'Edge (8 px)', 'Interior'],
                 ylabel='Error reduction (%)', title='B  Gains extend beyond the fixed band')
    ax[0, 1].axhline(0, color='.4', lw=.7)
    groups = sorted(df.group.unique())
    heat = df.groupby(['group', 'stage_third']).gain_B_STAR.mean().unstack().loc[groups]
    limit = float(np.abs(heat.to_numpy()).max())
    im = ax[1, 0].imshow(heat, cmap='RdBu', vmin=-limit, vmax=limit, aspect='auto')
    ax[1, 0].set(xticks=[0, 1, 2], xticklabels=['Early', 'Middle', 'Late'],
                 yticks=np.arange(19), yticklabels=groups,
                 title='C  Every release group retained: B* error - history error')
    ax[1, 0].tick_params(axis='y', labelsize=8)
    for label in ax[1, 0].get_yticklabels():
        if '30Deg' in label.get_text():
            label.set_color('#B2182B')
    fig.colorbar(im, ax=ax[1, 0], fraction=.04, pad=.025, label='Normalized error difference; blue = gain')
    match = pd.read_csv(out/'matched_descriptive_contrasts.csv')
    m = match[(match.adjustment == 'group_stage_horizon') & (match.comparator == 'B_STAR')]
    names = {'header_offset_flag': 'Header offset', 'margin_bin': 'Far vs near chunk edge',
             'threshold_range_px_third': 'Wide vs narrow setting range',
             'past10_mean_shift_mm_third': 'Large vs small mean shift',
             'current_roughness_ratio_third': 'High vs low roughness'}
    ax[1, 1].barh(np.arange(len(m)), m.mean_high_minus_low_gain, color='#009E73', height=.55)
    ax[1, 1].set(yticks=np.arange(len(m)), yticklabels=[names[x] for x in m.proxy],
                 xlabel='High - low history gain (normalized error)',
                 title='D  Same group / stage third / horizon only')
    ax[1, 1].axvline(0, color='.4', lw=.7)
    ax[1, 1].invert_yaxis()
    for y, row in enumerate(m.itertuples()):
        ax[1, 1].annotate(f'n={row.groups_n} groups', (row.mean_high_minus_low_gain, y),
                           xytext=(5 if row.mean_high_minus_low_gain >= 0 else -5, 0),
                           textcoords='offset points', va='center',
                           ha='left' if row.mean_high_minus_low_gain >= 0 else 'right', fontsize=8)
    ax[1, 1].margins(x=.45)
    fig.suptitle('Frozen Mendeley predictions: stage, region and processing-risk associations', fontsize=14)
    fig.text(.5, .013, '19 development-exposed release groups; H10/H40; no refit. Proxies are not measurement uncertainty. Original control defect retained.', ha='center', fontsize=9)
    fig.tight_layout(rect=[0, .035, 1, .96], w_pad=2.5)
    fig.savefig(out/'history_locality_summary.png')
    fig.savefig(out/'history_locality_summary.pdf')
    plt.close(fig)
    with np.load(out/'normalized_gain_maps.npz', allow_pickle=False) as z:
        maps = z['equal_group_horizon_mean'][0]
    limit = np.abs(maps).max()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.3), layout='constrained')
    for ch, a in enumerate(axes):
        im = a.imshow(maps[ch], origin='upper', cmap='RdBu', vmin=-limit, vmax=limit)
        a.set(title=f'Channel {ch}: B* error - history error', xlabel='Published grid column', ylabel='Published grid row')
    fig.colorbar(im, ax=axes, label='Normalized absolute-error gain; blue = gain', shrink=.8)
    fig.suptitle('Mean spatial gain on the published grid (unregistered across groups)')
    fig.savefig(out/'mean_spatial_gain.png')
    plt.close(fig)
    fig, axes = plt.subplots(3, 4, figsize=(13, 10), layout='constrained')
    for r, g in enumerate([0, 8, 14]):
        with np.load(out/f'example_{g}.npz', allow_pickle=False) as z:
            arrays = [z['target'][1]-z['current'][1], z['baseline'][1]-z['current'][1],
                      z['history'][1]-z['current'][1], z['normalized_gain'][1]]
            group, origin = str(z['group']), int(z['origin'])
        limit = max(np.abs(x).max() for x in arrays[:3])
        gl = np.abs(arrays[-1]).max()
        for j, a in enumerate(axes[r]):
            v = gl if j == 3 else limit
            im = a.imshow(arrays[j], cmap='RdBu_r' if j < 3 else 'RdBu', vmin=-v, vmax=v, origin='upper')
            a.set(xticks=[0, 64, 127], yticks=[0, 64, 127])
            if r == 0:
                a.set_title(['Published increment', 'B* increment', 'History increment', 'B* error - history error'][j])
            if j == 0:
                a.set_ylabel(f'{group}\norigin {origin}, H40\nPublished grid row', fontsize=9)
            if r == 2:
                a.set_xlabel('Published grid column')
            if j == 2:
                fig.colorbar(im, ax=axes[r, :3], label='Published displacement increment (mm)', shrink=.7)
            if j == 3:
                fig.colorbar(im, ax=a, label='Normalized gain', shrink=.7)
    fig.suptitle('Fixed middle-third median origins; channel 1; failure group retained\nSource identity selection, no score-based case selection; no crack-tip labels')
    fig.savefig(out/'fixed_field_examples.png')
    plt.close(fig)
    d = pd.read_csv(out/'boundary_raw_vs_pt_source_pairs.csv')
    names = ['mean_shift_mm', 'raw_shared_node_mean_shift_mm', 'shape_shift_mm', 'raw_shared_node_shape_shift_mm']
    ratios = []
    for col in names:
        pair = d.pivot(index=['group', 'boundary_stage'], columns='kind', values=col)
        ratios.append((pair.boundary/pair.preceding_control).to_numpy())
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), layout='constrained')
    axes[0].boxplot(ratios, tick_labels=['PT mean', 'CSV mean', 'PT shape', 'CSV shape'], showfliers=True)
    axes[0].set(yscale='log', ylabel='Boundary step / preceding within-chunk step',
                title='A  All 167 boundaries; controls fixed 10 steps earlier')
    axes[0].axhline(1, lw=.8, ls='--', color='.4')
    for j, x in enumerate(ratios):
        axes[0].text(j+1, np.max(x)*1.1, f'median {np.median(x):.2f}', ha='center', fontsize=8)
    for kind, color in [('boundary', '#D55E00'), ('preceding_control', '#0072B2')]:
        x = d[d.kind == kind]
        axes[1].scatter(x.raw_shared_node_mean_shift_mm, x.mean_shift_mm, s=12, alpha=.65, color=color, label=kind)
    bounds = [min(d.raw_shared_node_mean_shift_mm.min(), d.mean_shift_mm.min()),
              max(d.raw_shared_node_mean_shift_mm.max(), d.mean_shift_mm.max())]
    axes[1].plot(bounds, bounds, '--', color='.4', lw=.8)
    axes[1].set(xscale='log', yscale='log', xlabel='CSV shared-node mean step (mm)',
                ylabel='PT mean step (mm)', title='B  Mean-step signal already present in raw CSV')
    axes[1].legend(frameon=False, fontsize=8)
    fig.suptitle('Source processing check: association with chunks is not proof of an interpolation artifact')
    fig.savefig(out/'boundary_source_audit.png')
    plt.close(fig)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    plot(p.parse_args().out)

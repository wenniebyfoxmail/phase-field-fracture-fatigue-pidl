"""S02-E007: frozen sixth-epoch ISTRUST inference. No training or observation-noise arms."""
from __future__ import annotations
import argparse, copy, csv, hashlib, importlib, json, os, random, shutil, sys, time
from pathlib import Path


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def ordered_groups(names):
    """Pure filename manifest for the author's sorted loader and actual window indices."""
    groups = {}
    for name in sorted(names):
        if not name.endswith('.tiff'):
            raise ValueError(f'Unexpected dataset member: {name}')
        specimen, camera, seconds, fractional = name[:-5].split('_')
        if camera not in ('0', '1') or not specimen.startswith('A'):
            raise ValueError(name)
        rul = float(seconds) + float('0.' + fractional)
        if rul < 4000 and specimen != 'A025':
            g = groups.setdefault((specimen, int(camera)), {})
            if rul in g:
                raise ValueError('Duplicate parsed RUL within camera')
            g[rul] = name
    result = []
    for (specimen, camera), records in sorted(groups.items()):
        rows = [(rul, records[rul]) for rul in sorted(records, reverse=True)]
        trim = 8 if len(rows) % 2 == 0 else 9
        result.append({'specimen': specimen, 'camera': camera, 'rows': rows[trim:][1::2]})
    if [g['specimen'] for g in result[-2:]] != ['A020', 'A020']:
        raise ValueError('The author final-pair exclusion is not A020')
    return result[:-2]


def windows(groups):
    rows = []
    for g in groups:
        for j in range(len(g['rows']) - 7):
            inp = [g['rows'][j + k] for k in (0, 3, 6)]
            target = g['rows'][j + 7]
            rows.append({'specimen': g['specimen'], 'camera': g['camera'], 'window': j,
                         'input_files': [x[1] for x in inp], 'target_file': target[1],
                         'target_s': target[0], 'latest_input_rul_s': inp[-1][0],
                         'input_to_target_s': inp[-1][0] - target[0],
                         'elapsed_target_s': round(g['rows'][0][0] - target[0], 2)})
    return rows


def load_author(source, patched):
    """Retain original source; make exactly the one approved ordering correction in a copy."""
    shutil.copytree(source, patched)
    file = patched / 'istrust_model/data_gen.py'
    before = file.read_text()
    old = 'for i in os.listdir(directory_dataset):'
    new = 'for i in sorted(os.listdir(directory_dataset)):'
    if before.count(old) != 1:
        raise ValueError('Author source differs from the reviewed loader')
    file.write_text(before.replace(old, new))
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(patched / 'istrust_model'))
    return {name: importlib.import_module(name) for name in ['data_gen', 'data', 'utils', 'params', 'model']}


def prepare(root, config, source, raw, author):
    import numpy as np
    import torch
    import torchvision
    cache = root / 'cache'
    cache.mkdir()
    groups = ordered_groups(p.name for p in raw.iterdir() if p.is_file())
    expected = [(s, v) for s in config['active_specimens'] for v in (0, 1)]
    if [(g['specimen'], g['camera']) for g in groups] != expected:
        raise ValueError('Specimen/view membership differs from the frozen map')
    raw_groups, dp = author['data_gen'].load_raw_dataset(str(raw), str(source / 'istrust_model/hyperparams/data_params_init.json'))
    raw_groups = raw_groups[:-2]
    if len(raw_groups) != len(groups):
        raise ValueError('Sorted author loader group count disagrees with manifest')
    for actual, declared in zip(raw_groups, groups):
        if [x[0] for x in actual] != [x[0] for x in declared['rows']]:
            raise ValueError('Author loader and explicit manifest have different histories')
    report = []
    for fold, specimen in enumerate(config['fold_test_specimens'], 1):
        selected = [i for i, g in enumerate(groups) if g['specimen'] == specimen]
        assert len(selected) == 2
        train_indices = [i for i in range(len(groups)) if i not in selected]
        if set(groups[i]['specimen'] for i in selected) & set(groups[i]['specimen'] for i in train_indices):
            raise ValueError('Physical-specimen leakage')
        params = copy.copy(dp)
        params.validation_set_exists = False
        datasets = {}
        manifests = {}
        for split, indices in [('training_eval', train_indices), ('testing', selected)]:
            # Author routines mutate only row containers; preserve image tensors and original lists.
            rs = [[list(row) for row in raw_groups[i]] for i in indices]
            ds = author['data'].BuildDataset(*author['data_gen'].create_targets(rs, True, params), True)
            ds.pictures = author['utils'].normalize_images(torchvision.transforms.functional.equalize(ds.pictures), 255)
            datasets[split] = ds
            manifests[split] = windows([groups[i] for i in indices])
            if len(ds) != len(manifests[split]):
                raise ValueError('Window manifest length mismatch')
            np.testing.assert_allclose(ds.RUL_target[:, 0].numpy(), [r['target_s'] for r in manifests[split]], atol=0.001, rtol=0)
        train = datasets['training_eval']
        maximum = float(torch.max(train.RUL_target[:, 0]))
        mean, std = author['utils'].mean_std_calculator(train.pictures, 255)
        run = next((source / 'istrust_model/runs').glob(f'window_size_7_test_{fold}-*'))
        stored = json.loads((run / 'data_params.json').read_text())
        delta = {'mean': float(mean) - stored['mean'], 'std': float(std) - stored['std'],
                 'max_train': maximum - stored['max_train']}
        row = {'fold': fold, 'test_specimen': specimen, 'stored': stored,
               'regenerated': {'mean': float(mean), 'std': float(std), 'max_train': maximum},
               'differences': delta, 'run_folder': run.name}
        report.append(row)
        write_json(root / 'preprocessing_audit.json', report)
        if abs(delta['max_train']) > config['normalization_max_train_atol'] or any(abs(delta[k]) > config['normalization_mean_std_atol'] for k in ['mean', 'std']):
            raise ValueError(f'Normalization provenance mismatch before inference: fold {fold}: {delta}')
        for split, ds in datasets.items():
            expected_n = config['expected_train_windows' if split == 'training_eval' else 'expected_test_windows'][fold - 1]
            if len(ds) != expected_n:
                raise ValueError('Unexpected fold sample count')
            ds.RUL_target = ds.RUL_target / maximum
            ds.save(str(cache / f'fold{fold}_{split}.pth'))
            write_json(cache / f'fold{fold}_{split}.json', manifests[split])
        print(json.dumps({'event': 'preprocessed', 'fold': fold, 'differences': delta}), flush=True)
    return report


def tensor_load(path, torch):
    return torch.load(path, weights_only=True, map_location='cpu')


def evaluate_dataset(ds, manifest, encoder, predictor, stored, config, draws, seed, bands, author):
    import numpy as np
    import torch
    from torch.utils.data import DataLoader
    # Reset every stream explicitly; seeds are fixed before looking at forecasts.
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    ds.set_skip_images(3)
    loader = DataLoader(ds, batch_size=config['batch_size'], shuffle=False, num_workers=0)
    collected, losses, batch_ns = [], [], []
    with torch.no_grad():
        for inputs, targets, times_, experiment_ in loader:
            x = inputs.to('cuda', dtype=torch.float32) / 255
            x = (x - stored['mean']) / stored['std']
            y = targets.to('cuda')
            samples = []
            for _ in range(draws):
                features, attention_ = encoder(x)
                samples.append(predictor(features))
            predicted = torch.stack(samples, dim=-1).reshape(len(x), draws)
            predicted = predicted * stored['max_train'] + stored['min_train']
            values = predicted.cpu().numpy()
            if not np.isfinite(values).all():
                raise ValueError('Nonfinite RUL prediction')
            means = np.array([v.mean() for v in values])
            loss = torch.nn.functional.l1_loss((torch.from_numpy(means).cuda() - stored['min_train']) / stored['max_train'], y[:, 0])
            collected.append(values)
            losses.append(float(loss))
            batch_ns.append(len(x))
    values = np.concatenate(collected)
    means = np.array([v.mean() for v in values])
    # Use the float32 labels actually consumed by the original scoring routine.
    targets_n = ds.RUL_target[:, 0].numpy()
    direct = float(np.mean(np.abs((means - stored['min_train']) / stored['max_train'] - targets_n)))
    weighted = float(np.average(losses, weights=batch_ns))
    if abs(direct - weighted) > 1e-6:
        raise ValueError('Direct and original last-batch-weighted MAE disagree')
    rows = []
    for i, meta in enumerate(manifest):
        row = dict(meta)
        row['input_files'] = '|'.join(row['input_files'])
        target_s = float(targets_n[i] * stored['max_train'] + stored['min_train'])
        row.update(predicted_mean_s=float(means[i]), scored_target_s=target_s,
                   abs_error_s=abs(float(means[i]) - target_s), normalized_abs_error=float(abs((means[i] - stored['min_train']) / stored['max_train'] - targets_n[i])))
        if bands:
            ci, _ = author['utils'].confidence_intervals(values[i], .95)
            row.update(author_band_low_s=float(means[i] - ci.low), author_band_high_s=float(means[i] + ci.high))
        rows.append(row)
    return values, rows, {'n': len(rows), 'normalized_mae': direct, 'author_weighted_batch_mae': weighted,
                         'mae_s': float(np.mean([r['abs_error_s'] for r in rows])),
                         'nonfinite_band_rows': sum(not np.isfinite(r.get('author_band_low_s', 0)) or not np.isfinite(r.get('author_band_high_s', 0)) for r in rows)}


def run(root, config, source, cache, author, run_id, seed):
    import numpy as np
    import torch
    output = root / 'runs' / run_id
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for fold in range(1, 7):
        folder = next((source / 'istrust_model/runs').glob(f'window_size_7_test_{fold}-*'))
        mp = author['params'].ModelParams(str(folder / 'model_params.json'))
        dp = author['params'].DataParams(str(folder / 'data_params.json'))
        tp = author['params'].TrainingParams(str(folder / 'training_params.json'))
        dp.from_model(mp)
        torch.manual_seed(seed + fold)
        encoder = author['model'].Encoder(dp, mp, tp, 's2').cuda()
        predictor = author['model'].Predictor(mp).cuda()
        encoder.load_state_dict(tensor_load(folder / 'stage_2/encoder_state_dict_epoch_bn_6.pt', torch), strict=True)
        predictor.load_state_dict(tensor_load(folder / 'stage_2/predictor_state_dict_epoch_6.pt', torch), strict=True)
        encoder.eval()
        encoder.change_dropout(dropout=.3, mc_dropout=True)
        predictor.eval()
        if any(m.training for m in encoder.modules() if isinstance(m, torch.nn.BatchNorm2d)):
            raise ValueError('BatchNorm entered training mode')
        if any(not m.training or m.p != .3 for m in encoder.modules() if isinstance(m, torch.nn.Dropout)):
            raise ValueError('MC dropout mode mismatch')
        saved_state = {f'e:{k}': v.detach().cpu().clone() for k, v in encoder.state_dict().items()}
        saved_state.update({f'p:{k}': v.detach().cpu().clone() for k, v in predictor.state_dict().items()})
        for split in ['training_eval', 'testing']:
            ds = author['data'].BuildDataset(*tensor_load(cache / f'fold{fold}_{split}.pth', torch))
            manifest = json.loads((cache / f'fold{fold}_{split}.json').read_text())
            streams = [(config['mc_draws'], seed + fold * 100 + (0 if split == 'training_eval' else 1), split == 'testing')]
            if split == 'testing' and run_id == config['run_ids'][0]:
                streams.append((5, config['five_draw_estimator_seed'] + fold, False))
            for n_draws, stream, bands in streams:
                values, rows, metrics = evaluate_dataset(ds, manifest, encoder, predictor, dp.__dict__, config, n_draws, stream, bands, author)
                stem = f'fold{fold}_{split}_mc{n_draws}'
                np.savez_compressed(output / f'{stem}_draws.npz', draws_s=values)
                with (output / f'{stem}.csv').open('w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                    writer.writeheader(); writer.writerows(rows)
                record = dict(run_id=run_id, seed=seed, stream_seed=stream, fold=fold, split=split, draws=n_draws, **metrics)
                results.append(record)
                write_json(output / 'metrics.json', results)
                print(json.dumps({'event': 'scored', **record}), flush=True)
        current = {f'e:{k}': v.detach().cpu() for k, v in encoder.state_dict().items()}
        current.update({f'p:{k}': v.detach().cpu() for k, v in predictor.state_dict().items()})
        if not all(torch.equal(v, current[k]) for k, v in saved_state.items()):
            raise ValueError('Parameters or BatchNorm buffers changed during evaluation')
        del encoder, predictor, ds
        torch.cuda.empty_cache()
    write_json(output / 'completion.json', {'run_id': run_id, 'seed': seed, 'complete': True, 'training_steps': 0,
                                           'observation_uncertainty_testing': False, 'state_unchanged': True})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--dataset', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if config['training'] or config['observation_uncertainty_testing'] or config['epoch'] != 6:
        raise ValueError('Scope differs from sixth-epoch no-training replay')
    import torch, torchvision, numpy, PIL, scipy, matplotlib
    actual = {'python': '.'.join(map(str, sys.version_info[:3])), 'torch': torch.__version__,
              'torchvision': torchvision.__version__, 'numpy': numpy.__version__, 'Pillow': PIL.__version__,
              'scipy': scipy.__version__, 'matplotlib': matplotlib.__version__}
    write_json(args.root / 'runtime.json', {'versions': actual, 'cuda_runtime': torch.version.cuda,
                                         'gpu_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                                         'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES')})
    if actual != config['runtime'] or not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise ValueError(f'Runtime/device mismatch: {actual}')
    torch.set_num_threads(config['threads'])
    author = load_author(args.source, args.root / 'patched_author')
    prepare(args.root, config, args.source, args.dataset, author)
    for run_id, seed in zip(config['run_ids'], config['seeds']):
        run(args.root, config, args.source, args.root / 'cache', author, run_id, seed)
    write_json(args.root / 'completion.json', {'complete': True, 'run_ids': config['run_ids'], 'epoch': 6,
                                              'training_steps': 0, 'observation_uncertainty_testing': False})


if __name__ == '__main__':
    main()

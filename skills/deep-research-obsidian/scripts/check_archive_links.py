#!/usr/bin/env python3
"""Check vault wikilinks in selected notes. No writes or content verification."""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


def check(vault, notes):
    index = defaultdict(list)
    for item in vault.rglob('*'):
        if item.is_file() and not any(p.startswith('.') for p in item.relative_to(vault).parts):
            index[item.name].append(item)
            if item.suffix == '.md':
                index[item.stem].append(item)
    issues = []
    checked = 0
    for note in notes:
        if not note.is_file():
            issues.append({'note': str(note), 'error': 'note_missing'})
            continue
        for raw in re.findall(r'!?\[\[([^\]]+)\]\]', note.read_text(encoding='utf-8')):
            target = raw.split('|', 1)[0].split('#', 1)[0].strip()
            if not target:
                continue
            checked += 1
            matches = list(dict.fromkeys(index.get(target, [])))
            if '/' in target:
                path = vault / target
                md_path = Path(str(path) + '.md')
                matches = [path] if path.is_file() else [md_path] if md_path.is_file() else []
            if len(matches) != 1:
                issues.append({'note': str(note), 'link': target, 'matches': len(matches)})
    return {'checked_links': checked, 'issues': issues,
            'scope': 'existence and uniqueness only; not paper identity or scientific verification'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', type=Path, required=True)
    parser.add_argument('notes', type=Path, nargs='+')
    args = parser.parse_args()
    if not args.vault.is_dir():
        parser.error('vault must be an existing directory')
    result = check(args.vault.resolve(), args.notes)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(result['issues']))


if __name__ == '__main__':
    raise SystemExit(main())

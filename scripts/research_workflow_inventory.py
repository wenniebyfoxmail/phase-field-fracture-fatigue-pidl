#!/usr/bin/env python3
"""Read-only inventory of research agent roots and installed workflow entrypoints."""
import argparse
import json
import sqlite3
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path


def git(path, *args):
    result = subprocess.run(['git', '-C', str(path), *args], text=True,
                            capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=Path('/Users/wenxiaofang/.codex/state_5.sqlite'))
    parser.add_argument('--repo', type=Path, default=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code'))
    parser.add_argument('--days', type=int, default=7)
    args = parser.parse_args()
    db = sqlite3.connect(f'{args.database.as_uri()}?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    since = int((datetime.now(timezone.utc) - timedelta(days=args.days)).timestamp())
    rows = db.execute('SELECT id,cwd,source,rollout_path,updated_at FROM threads WHERE archived=0 AND updated_at>=?', (since,)).fetchall()
    prefixes = ('/Users/wenxiaofang/phase-field-fracture-with-pidl',
                '/Users/wenxiaofang/0 idea test', '/Users/wenxiaofang/Supervised method',
                '/Users/wenxiaofang/0 project/', '/Users/wenxiaofang/Documents/ChatGPT/cacaie')
    threads = []
    for row in rows:
        if not row['cwd'].startswith(prefixes):
            continue
        source = row['source']
        parent = None
        agent_path = None
        if source.startswith('{'):
            try:
                spawn = json.loads(source).get('subagent', {}).get('thread_spawn', {})
                parent, agent_path = spawn.get('parent_thread_id'), spawn.get('agent_path')
            except ValueError:
                pass
        threads.append({'id': row['id'], 'cwd': row['cwd'], 'parent': parent,
                        'agent_path': agent_path, 'updated_at': row['updated_at']})
    blocks = (git(args.repo, 'worktree', 'list', '--porcelain') or '').split('\n\n')
    worktrees = []
    for block in blocks:
        lines = block.splitlines()
        if not lines:
            continue
        path = Path(lines[0].removeprefix('worktree '))
        historical = any(token in path.name for token in ('recovery', 'historical', 'runtime-'))
        text = (path/'AGENTS.md').read_text() if (path/'AGENTS.md').exists() else ''
        override = path/'AGENTS.override.md'
        worktrees.append({'path': str(path), 'kind': 'historical-snapshot' if historical else 'research-workspace',
                          'core_in_agents': 'research-decision-core' in text,
                          'override_exists': override.is_file(),
                          'bootstrap_current': override.is_file() and
                          'research-decision-core/references/agent_bootstrap.md' in override.read_text(),
                          'branch': next((x.removeprefix('branch ') for x in lines if x.startswith('branch ')), None)})
    skills = {}
    for name in ('research-decision-core', 'road-fracture-experiment-gate', 'pidl-experiment-gate',
                 'research-figure-workflow', 'deep-research-obsidian'):
        path = Path('/Users/wenxiaofang/.codex/skills')/name/'SKILL.md'
        skills[name] = {'exists': path.is_file(), 'resolved': str(path.resolve())}
    print(json.dumps({'observed_at_utc': datetime.now(timezone.utc).isoformat(),
                      'recent_threads': threads, 'worktrees': worktrees, 'global_entries': skills},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

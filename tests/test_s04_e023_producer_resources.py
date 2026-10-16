"""Exercise real shell resource guards with temporary local command shims; no GPU."""
from pathlib import Path
import os
import subprocess

import pytest

PRODUCER = Path(__file__).resolve().parents[1] / "docs/research/S04/S04-E023/producer"


@pytest.mark.parametrize(
    "version,free_mib,disk_kb,existing,drift,query_failure,passes",
    [
        ("v2", 21772, 600000000, True, False, True, False),
        ("v2", 21772, 600000000, True, False, False, True),
        ("v2", 8192, 600000000, True, False, False, False),
        ("v2", 21772, 8388608, True, False, False, False),
        ("v2", 21772, 600000000, False, False, False, True),
        ("v2", 21772, 600000000, True, True, False, False),
    ],
)
def test_actual_resource_function(
    tmp_path, version, free_mib, disk_kb, existing, drift, query_failure, passes
):
    script = PRODUCER / "prepare_and_dispatch.sh"
    body = (
        script.read_text()
        .split("resource_check() {", 1)[1]
        .split("\n}\nresource_check initial", 1)[0]
    )
    tools, root = tmp_path / "bin", tmp_path / "root"
    tools.mkdir()
    (root / "logs").mkdir(parents=True)
    if drift:
        (root / "gpu0.uuid").write_text("different-uuid\n")
    apps = "GPU-test, 12345\\n" if existing else ""
    commands = {
        "mountpoint": "exit 0",
        "df": f"""if [ "$1" = -Pk ]; then
printf 'Filesystem 1024-blocks Used Available Capacity Mounted\\n/dev/test 999999999 1 {disk_kb} 1%% /mnt/data2\\n'
else printf 'test disk\\n'; fi""",
        "nvidia-smi": f"""case "$*" in
 *--query-gpu=memory.free*) {'exit 17' if query_failure else f'printf {free_mib}'} ;;
 *--query-gpu=uuid*) printf 'GPU-test\\n' ;;
 *--query-compute-apps=*) printf '{apps}' ;;
 *) printf 'test gpu telemetry\\n' ;;
esac""",
    }
    for name, command in commands.items():
        p = tools / name
        p.write_text("#!/bin/sh\n" + command + "\n")
        p.chmod(0o755)
    harness = (
        'set -Eeuo pipefail\nROOT="$E023_TEST_ROOT"\nresource_check() {'
        + body
        + "\n}\nresource_check test\n"
    )
    env = dict(
        os.environ,
        E023_TEST_ROOT=str(root),
        PATH=str(tools) + os.pathsep + os.environ["PATH"],
    )
    result = subprocess.run(
        ["/bin/bash"], input=harness, text=True, env=env, capture_output=True
    )
    assert (result.returncode == 0) is passes, result.stderr
    if passes:
        assert (root / "gpu0.uuid").read_text() == "GPU-test\n"
        assert (
            bool((root / "logs/test_compute_apps.txt").read_text().strip()) is existing
        )

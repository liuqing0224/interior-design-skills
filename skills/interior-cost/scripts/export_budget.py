#!/usr/bin/env python3
"""Run the artifact-tool author in a temporary workspace with bundled dependencies."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

def main():
    p=argparse.ArgumentParser();p.add_argument('project',type=Path);p.add_argument('--node',type=Path);p.add_argument('--modules',type=Path);a=p.parse_args()
    bundled=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
    node=a.node or bundled/'bin/node';modules=a.modules or bundled/'node_modules'
    if not node.is_file() or not (modules/'@oai/artifact-tool').exists():raise SystemExit('Provide bundled --node and --modules paths from load_workspace_dependencies')
    with tempfile.TemporaryDirectory(prefix='interior-budget-') as tmp:
        work=Path(tmp);(work/'node_modules').symlink_to(modules.resolve(),target_is_directory=True)
        shutil.copyfile(Path(__file__).with_name('build_budget.mjs'),work/'build_budget.mjs')
        return subprocess.run([str(node),str(work/'build_budget.mjs'),str(a.project.resolve())],cwd=work).returncode

if __name__=='__main__':raise SystemExit(main())

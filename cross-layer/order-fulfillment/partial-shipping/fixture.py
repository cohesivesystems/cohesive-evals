"""Materialize the pinned shipping fixtures, then apply only the offline quantity evolution."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'case-discovery'))
from grade import call, install_source
from prepare import APP, CONDITIONS, build


def fixtures(output):
    """Build isolated, locked reference applications and install the shared proposal protocol."""
    build(output)
    for condition in CONDITIONS:
        folder = output / condition
        subprocess.run(['git', 'apply', str(ROOT / 'reference' / f'{condition}.patch')], cwd=folder, check=True)
        for name in ['Program.cs', 'Cases.cs']:
            shutil.copyfile(ROOT / 'scaffold' / name, folder / 'Suite' / name)
        shutil.copyfile(ROOT / 'scaffold' / f'{condition}.cs', folder / 'Suite/Adapter.cs')
        shutil.copyfile(ROOT / 'task.md', folder / 'task.md')
        compile_suite(folder)


def compile_suite(folder):
    """Recompile the application and public adapter; a compilation error blocks grading."""
    subprocess.run(['dotnet', 'build', 'Suite/Suite.csproj', '--no-restore', '--no-incremental'],
                   cwd=folder, check=True, timeout=90)


if __name__ == '__main__':
    fixtures(Path(sys.argv[1]).resolve())

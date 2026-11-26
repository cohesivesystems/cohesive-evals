"""Publish both original G0 hosts with the pick-list endpoint in disposable folders."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
ARMS = ('conventional', 'cohesive')


def build(output):
    """Build locked Release applications; mismatched baseline anchors or builds abort setup."""
    for arm in ARMS:
        folder = output / arm
        shutil.copytree(ROOT.parent / 'conditions' / arm, folder)
        app = folder / 'src/Fulfillment.Application'
        program = app / 'Program.cs'
        anchor = 'HostSetup.Configure(app);'
        source = program.read_text()
        if source.count(anchor) != 1:
            raise ValueError('G0 endpoint registration changed')
        program.write_text(source.replace(anchor, anchor + '\nawait app.MapPickList();'))
        candidate = ROOT / 'candidate'
        if arm == 'cohesive':
            subprocess.run(['git', 'apply', str(candidate/'cohesive.patch')], cwd=folder, check=True)
        shutil.copyfile(candidate / 'PickList.cs', app / 'PickList.cs')
        subprocess.run(['dotnet', 'restore', '--locked-mode'], cwd=app, check=True)
        published = folder / 'published'
        subprocess.run(['dotnet', 'publish', '--no-restore', '-c', 'Release', '-p:UseAppHost=false',
                        '-o', str(published)], cwd=app, check=True)
        (published / 'pick-schema.sql').write_text((candidate / f'{arm}.sql').read_text() +
                                                   (candidate / 'stock.sql').read_text())
        shutil.copyfile(candidate / 'pick-list.sql', published / 'pick-list.sql')


if __name__ == '__main__':
    build(Path(sys.argv[1]).resolve())

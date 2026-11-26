"""Tabulate individual run results and median scale ratios from the complete evidence panel."""
import json
from pathlib import Path
from statistics import median
import sys


def summarize(root):
    """Require twelve distinct measured runs and report CPU and buffer work per write."""
    rows = []
    by_arm = {}
    for scale in [100000, 1000000]:
        for rep in range(1, 4):
            for arm in ('conventional','cohesive'):
                folder = root / f'{scale}-{rep}-{arm}'
                if (folder/'failure.json').exists():
                    raise ValueError(f'Failed run: {folder}')
                r = json.loads((folder/'report.json').read_text())
                if (r['orders'],r['arm'],r['writes'],r['reads']) != (scale,arm,6000,19200):
                    raise ValueError(f'Wrong measured workload: {folder}')
                db_ms = r['cpuSeconds']['db']*1000/r['writes']
                app_ms = r['cpuSeconds']['app']*1000/r['writes']
                hits = r['bufferHitsPerWrite']
                reads = r['bufferReadsPerWrite']
                rows.append(f"| {scale:,} | {rep} | {arm} | {r['foregroundP99Ms']:.1f} | "
                            f"{r['visibilityP99Ms']:.1f} | {db_ms:.2f} | {app_ms:.2f} | {hits:.1f} | {reads:.2f} |")
                by_arm.setdefault((arm,scale),[]).append((db_ms,hits+reads,app_ms))
    table = ['| Orders | Run | Condition | GET p99 ms | Visibility p99 ms | DB CPU ms/write | App CPU ms/write | Buffer hits/write | Reads/write |',
             '|---:|---:|---|---:|---:|---:|---:|---:|---:|', *rows]
    for arm in ('conventional','cohesive'):
        small = by_arm[arm,100000]
        large = by_arm[arm,1000000]
        ratios = [median(v[i] for v in large)/median(v[i] for v in small) for i in range(3)]
        table += ['', f'{arm.capitalize()}, 1M / 100k median work per write: DB CPU {ratios[0]:.2f}×, '
                      f'total buffer accesses {ratios[1]:.2f}×, app CPU {ratios[2]:.2f}×.']
    return '\n'.join(table)+'\n'


if __name__ == '__main__':
    print(summarize(Path(sys.argv[1])),end='')

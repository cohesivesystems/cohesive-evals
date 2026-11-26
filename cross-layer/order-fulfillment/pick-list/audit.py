"""Cross-check retained HTTP hashes and submitted load against the pre-authoring freeze."""
from collections import Counter
import gzip
import json
from math import ceil
from pathlib import Path
import sys

from workload import freeze, trace


def audit_run(folder, golden):
    """Reject missing, duplicate or incorrect samples, and verify reported p99s from raw events."""
    report = json.loads((folder / 'report.json').read_text())
    pages = golden['pages']
    expected = {}
    for i, (location, _, _, _) in enumerate(trace()):
        expected[i] = pages[location][1 + (i // 32) % 4]

    counts = Counter()
    reads, commits, first_seen = {}, set(), {}
    with gzip.open(folder / 'samples.jsonl.gz', 'rt') as records:
        for line in records:
            kind, index, _, latency, observed = json.loads(line)
            counts[kind] += 1
            if kind == 'write':
                if observed != expected[index] or index in commits:
                    raise ValueError(f'{folder.name}: unexpected write {index}')
                commits.add(index)
            elif kind == 'read':
                if index in reads or observed not in pages[f'L{index % 32:02}']:
                    raise ValueError(f'{folder.name}: duplicate read or unknown page at {index}')
                reads[index] = latency
            elif kind == 'probe':
                if observed not in pages[f'L{index % 32:02}']:
                    raise ValueError(f'{folder.name}: unknown probe page at {index}')
                if observed == expected[index]:
                    first_seen.setdefault(index, latency)
            else:
                raise ValueError(f'Unknown sample kind {kind}')

    if set(reads) != set(range(19200)) or commits != set(range(6000)):
        raise ValueError(f'{folder.name}: incomplete workload {counts}')
    visible = [first_seen.get(i, float('inf')) for i in range(6000)]
    for metric, samples in [('foregroundP99Ms', list(reads.values())), ('visibilityP99Ms', visible)]:
        observed = sorted(samples)[ceil(.99*len(samples))-1]
        if observed != report[metric]:
            raise ValueError(f'{folder.name}: {metric} mismatch')
    if sum(value > 2000 for value in visible) != report['overTwoSeconds']:
        raise ValueError(f'{folder.name}: visibility deadline count mismatch')
    return counts


if __name__ == '__main__':
    root = Path(sys.argv[1])
    golden = freeze()
    total = Counter()
    for scale in (100000, 1000000):
        for repetition in range(1, 4):
            for condition in ('conventional', 'cohesive'):
                total.update(audit_run(root / f'{scale}-{repetition}-{condition}', golden))
    print(dict(total))

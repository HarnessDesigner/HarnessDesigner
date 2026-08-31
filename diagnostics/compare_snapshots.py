# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Diff two heap snapshots saved by the ``"heap_snapshot"`` diagnostics
command (see harness_designer/memory_diagnostics.py).

Unlike the live ``"growth"`` command, this works on snapshots taken
arbitrarily far apart -- including across a process restart -- since each
snapshot is a file on disk under ``Config.debug.memory.snapshot_dir``, not
in-memory state tied to one running process.

Usage::

    python diagnostics/compare_snapshots.py <old.snapshot> <new.snapshot> [top_n]

Take an early snapshot (``heap_snapshot``) shortly after startup, do
whatever grows memory, take a second one, then diff them -- the ranked list
is by size *increase* between the two, so what's actually growing floats to
the top regardless of how large it already was in the first snapshot.
"""

import sys
import tracemalloc


def main():
    if len(sys.argv) < 3:
        print(f'usage: python {sys.argv[0]} <old.snapshot> <new.snapshot> [top_n]')
        sys.exit(1)

    old_path, new_path = sys.argv[1], sys.argv[2]
    top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    old = tracemalloc.Snapshot.load(old_path)
    new = tracemalloc.Snapshot.load(new_path)

    diff = new.compare_to(old, 'lineno')

    print(f'DIFF: {old_path} -> {new_path}')
    print(f'top {top_n} allocation sites by size increase:')
    for stat in diff[:top_n]:
        print(f'  {stat}')

    total_diff = sum(stat.size_diff for stat in diff)
    total_new = sum(stat.size for stat in new.statistics('lineno'))
    print()
    print(f'total traced size change: {total_diff / 1024 / 1024:+.2f} MB')
    print(f'total traced size (new snapshot): {total_new / 1024 / 1024:.2f} MB')


if __name__ == '__main__':
    main()

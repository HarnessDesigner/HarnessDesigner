# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Query a running harness_designer process's live memory diagnostics.

Only works while the app is running with ``Config.debug.memory.enabled``
set to True (see harness_designer/config.py and
harness_designer/memory_diagnostics.py) -- otherwise there's no listener
to connect to.

Usage::

    python diagnostics/query_memory.py tracemalloc
    python diagnostics/query_memory.py objects
    python diagnostics/query_memory.py growth
    python diagnostics/query_memory.py gpu
    python diagnostics/query_memory.py gpu_growth
    python diagnostics/query_memory.py displays
    python diagnostics/query_memory.py caches
    python diagnostics/query_memory.py stacks
    python diagnostics/query_memory.py rss
    python diagnostics/query_memory.py heap_snapshot

Run ``growth`` more than once, with real time passed (and no interaction,
or some specific interaction, in between) to see what object counts are
actually still climbing. ``gpu_growth`` works the same way, but for
``vram_use`` and a few correlating fields (temp, engine utilization, fan,
clocks) instead of Python object counts.

Hunting an unexplained total? Start with ``rss`` -- it says whether the
memory is even in the Python heap (``tracemalloc``/``growth`` can only ever
see that part) or native (Qt/OpenGL/C-extension buffers, which ``rss``
reports as the gap between OS-reported and traced memory, but can't break
down further itself). ``heap_snapshot`` saves a snapshot to disk for
``compare_snapshots.py`` to diff later; ``stacks`` shows what every thread
is doing at this instant, which can point at *where* a large allocation is
coming from even when it's not a leak so much as one code path holding onto
too much at once.
"""

import sys
from multiprocessing.connection import Client

_AUTHKEY = b'harness_designer-memory-diagnostics'
_DEFAULT_PORT = 47441

_COMMANDS = (
    'tracemalloc', 'objects', 'growth', 'gpu', 'gpu_growth', 'displays',
    'caches', 'stacks', 'rss', 'heap_snapshot',
)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in _COMMANDS:
        print(f'usage: python {sys.argv[0]} <{"|".join(_COMMANDS)}> [port]')
        sys.exit(1)

    command = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else _DEFAULT_PORT

    try:
        with Client(('localhost', port), authkey=_AUTHKEY) as conn:
            conn.send(command)
            print(conn.recv())
    except ConnectionRefusedError:
        print(f'could not connect to localhost:{port} -- is harness_designer running '
             f'with Config.debug.memory.enabled = True?')
        sys.exit(1)


if __name__ == '__main__':
    main()

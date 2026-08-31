# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
import sys

# Must be set before numpy is imported anywhere (including transitively, by
# the "import harness_designer" below) -- numpy's OpenBLAS backend reads
# these once, at import time, to size its thread-pool workspace buffers.
# Left unset, OpenBLAS reserves buffers for its build's max thread count
# (24 in this build) regardless of how many cores this machine has or
# whether anything here ever runs a large enough matrix operation to want
# that many threads -- measured at ~742MB of address-space reservation for
# a codebase that (checked directly) has no bulk matrix-matrix operations
# large enough to benefit from it. 2 threads measured ~41MB reserved (and a
# real speedup, not just less memory -- thread-coordination overhead on
# small ops was apparently costing more than any parallelism gained); 1
# thread measured ~9MB.
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')

# Installs a low-level signal handler that fires at the moment of a hard
# native crash (segfault/access violation/stack overflow) -- independent of
# normal Python exception propagation, so it still fires when a crash
# happens inside a C extension (Qt/PySide, numpy, sqlite3, ...) that never
# raises a catchable Python exception at all. Written to its own file
# (opened now, before harness_designer.logger repoints sys.stderr through
# its queued/threaded machinery) rather than sys.stderr -- a signal handler
# firing mid-crash needs a plain, already-open file it can write to
# directly, not one behind a background thread that may itself be in an
# inconsistent state, and a --windowed/frozen build has no real stderr to
# write to at all.
import faulthandler

_crash_log_dir = os.path.join(os.path.expanduser('~'), 'appdata', 'roaming', 'HarnessDesigner', 'log')
os.makedirs(_crash_log_dir, exist_ok=True)
_crash_log_path = os.path.join(_crash_log_dir, 'crash.log')
_crash_log_file = open(_crash_log_path, 'a', encoding='utf-8')
faulthandler.enable(file=_crash_log_file, all_threads=True)

import sys

_original_excepthook = sys.excepthook

def _patched_excepthook(exc_type, exc_value, exc_tb):
    import traceback
    print("UNHANDLED EXCEPTION:")
    traceback.print_exception(exc_type, exc_value, exc_tb)
    _original_excepthook(exc_type, exc_value, exc_tb)

sys.excepthook = _patched_excepthook

def excepthook(exc_type, exc_value, exc_tb):
    import traceback
    print("QT UNHANDLED EXCEPTION:", flush=True)
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

if __name__ == '__main__':
    import multiprocessing

    multiprocessing.set_start_method('spawn')

sys.path.insert(0, os.path.dirname(__file__))

import harness_designer


def main():
    harness_designer.__main__()


if __name__ == '__main__':
    main()

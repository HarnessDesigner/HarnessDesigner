# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
import sys

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

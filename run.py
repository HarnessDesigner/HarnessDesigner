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
import atexit
import datetime
import faulthandler
import multiprocessing
import multiprocessing.spawn


def _is_main_process() -> bool:
    """Whether this is the application's own process rather than a worker
    it spawned.

    The model and image workers are started with the ``spawn`` method,
    which re-runs this whole file in every one of them, so anything at the
    top level here happens once per worker as well. Two checks are needed
    because they cover different cases:

    - Started from source, a worker's name ("Process-N") is already set
      before this file is re-run, so it is no longer ``MainProcess``.
    - Frozen, a worker is a fresh run of the executable that still reports
      ``MainProcess`` until ``freeze_support()`` runs, but it carries
      ``--multiprocessing-fork`` on its command line.

    ``multiprocessing.parent_process()`` is no use here: it is only set
    after this file has been re-run.
    """
    if multiprocessing.current_process().name != 'MainProcess':
        return False

    return not multiprocessing.spawn.is_forking(sys.argv)


def _enable_native_crash_log() -> None:
    """Open this run's crash log and point faulthandler at it. Called for
    the main process only, so workers never create one: they would leave an
    empty file behind whenever they are killed instead of exiting normally.

    A worker that dies in native code therefore leaves no traceback of its
    own; its Python-level errors are still reported to the main process.
    """
    crash_log_dir = os.path.join(os.path.expanduser('~'), 'appdata', 'roaming', 'HarnessDesigner', 'log')
    os.makedirs(crash_log_dir, exist_ok=True)

    # Sweep away any EMPTY crash log left behind by a past run that never
    # actually crashed -- normally cleaned up by this same run's own
    # atexit hook below, but that hook can't run if THAT run ended by
    # being killed outright rather than exiting normally (no crash
    # either, just never got the chance). Never removes one with real
    # content in it.
    for name in os.listdir(crash_log_dir):
        if name.startswith('crash_') and name.endswith('.log'):
            old_path = os.path.join(crash_log_dir, name)
            try:
                if os.path.getsize(old_path) == 0:
                    os.remove(old_path)
            except OSError:
                pass

    # Named for THIS run's own start time, not the crash itself -- the
    # exact crash time isn't known in advance, and faulthandler needs this
    # file already open and ready before any crash can happen (same reason
    # it writes to a plain file instead of through logger's own queued/
    # threaded machinery, per the comment above) -- so there is no later
    # point to name it from. The file's own mtime still ends up reflecting
    # the real crash time, once something is actually written to it.
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    crash_log_path = os.path.join(crash_log_dir, f'crash_{stamp}.log')
    crash_log_file = open(crash_log_path, 'w', encoding='utf-8')
    faulthandler.enable(file=crash_log_file, all_threads=True)

    def remove_crash_log_if_unused() -> None:
        """Delete THIS run's own crash-log file if nothing was ever
        written to it -- faulthandler needs the file open and ready
        before any crash can happen, so one gets created on every launch
        regardless of whether a crash ever occurs; this removes it again
        on a normal exit, so only a run that actually crashed leaves one
        behind. Never runs at all if the process is killed outright
        rather than exiting normally -- see the startup sweep above for
        the leftover that leaves behind.
        """
        if crash_log_file.closed:
            return

        try:
            crash_log_file.flush()
            if os.path.getsize(crash_log_path) == 0:
                crash_log_file.close()
                os.remove(crash_log_path)
            else:
                crash_log_file.close()
        except OSError:
            pass

    atexit.register(remove_crash_log_if_unused)


if _is_main_process():
    _enable_native_crash_log()

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

    # An exception that reaches all the way here -- escaping every Qt
    # slot/event callback with nothing in between catching it -- is
    # exactly the fatal case this exists for: PySide6 (this build)
    # aborts the process right after sys.excepthook returns from one
    # of these, so this is the last safely-running Python code that
    # will ever see this app's live state. Not wired anywhere else
    # (an ordinarily-caught exception, like the per-object render
    # error canvas_base.py already catches and logs, never reaches
    # here at all) -- see harness_designer.crash_dump's own module
    # docstring for why a TRUE native crash (an access violation,
    # caught by faulthandler.enable() above instead) can't get this
    # same treatment: that one happens inside a C extension, with no
    # Python frame to resume into afterward.
    try:
        from harness_designer import crash_dump as _crash_dump
        _crash_dump.dump_state_on_fatal_exception(exc_type, exc_value, exc_tb)
    except Exception:  # NOQA -- a broken diagnostic must never mask the real exception
        pass

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

# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
import sys
import threading

try:
    from . import utils_
    from . import spawn
except ImportError:
    import utils_
    import spawn


error_lock = threading.Lock()

errors = []


def _cythonize_chunk(files, t_lock, sys_path):
    # Invoke cythonize from the command line (via spawn) instead of calling
    # Cythonize.main() in-process — spawn() serializes output through
    # print_lock, so N threads compiling concurrently don't interleave output.
    #
    # Cython may only be on sys.path via setup_requires (fetched into a
    # transient .eggs cache for this one process), so a fresh subprocess
    # started from sys.executable has no guarantee of finding it via -m.
    # -c explicitly re-inserts cython_path into sys.path before importing,
    # instead of relying on the subprocess's own default sys.path.
    for file in files:
        code = (
            f'import sys; sys.path.insert(0, {sys_path!r}); '
            f'from Cython.Build import Cythonize; '
            f"Cythonize.main(['-3', '--build', '--inplace', {file!r}])"
        )
        cmd = f'"{sys.executable}" -c "{code}"'
        rc, error_lines = spawn.spawn(cmd)
        if rc:
            with error_lock:
                errors.extend(error_lines)

    t_lock.release()


def run(hd_path):

    cfiles = utils_.iter_mod_path(hd_path)

    import Cython
    cython_path = os.path.abspath(os.path.join(os.path.dirname(Cython.__file__), '..'))

    n_threads = os.cpu_count()

    chunk_size, remainder = divmod(len(cfiles), n_threads)

    chunks = []
    start = 0
    for i in range(n_threads):
        size = chunk_size + (1 if i < remainder else 0)
        chunks.append(cfiles[start:start + size])
        start += size

    threads = []
    locks = []

    for chunk in chunks:
        lock = threading.Lock()
        lock.acquire()

        thread = threading.Thread(target=_cythonize_chunk, args=(chunk, lock, cython_path), daemon=True)
        thread.start()

        threads.append(thread)
        locks.append(lock)

    for lock in locks:
        lock.acquire()

    if errors:
        for line in errors:
            sys.stderr.write(line + '\n')
        sys.stderr.flush()
        sys.exit(1)

    utils_.cleanup_after_compile(hd_path)

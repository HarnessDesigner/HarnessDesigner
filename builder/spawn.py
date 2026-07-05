# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import sys
import os
import subprocess
import threading


if sys.platform.startswith('win'):
    SHELL = 'cmd'
else:
    SHELL = 'bash'


DUMMY_RETURN = b''

print_lock = threading.Lock()


def spawn(cmd):
    cmd += '\n'
    cmd = cmd.encode('utf-8')

    if sys.platform.startswith('win'):
        p = subprocess.Popen(
            SHELL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            env=os.environ
        )
    else:
        p = subprocess.Popen(
            SHELL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            env=os.environ
        )

    p.stdin.write(cmd)
    p.stdin.close()

    error_lines = []

    while p.poll() is None:
        for line in iter(p.stdout.readline, DUMMY_RETURN):
            line = line.strip()
            if line:
                with print_lock:
                    if sys.platform.startswith('win'):
                        sys.stdout.write(line.decode('utf-8') + '\n')
                    else:
                        sys.stdout.write(line.decode('utf-8') + '\n')

                    sys.stdout.flush()

        # Error output is collected, not printed here — callers decide
        # whether/when to surface it (e.g. only after a whole batch of
        # spawned commands has finished, to avoid interleaved output).
        for line in iter(p.stderr.readline, DUMMY_RETURN):
            line = line.strip()
            if line:
                error_lines.append(line.decode('utf-8'))

    if not p.stdout.closed:
        p.stdout.close()

    if not p.stderr.closed:
        p.stderr.close()

    sys.stdout.flush()

    returncode = p.returncode

    # cmd is piped into a bare shell's stdin rather than run directly
    # (`cmd.exe`/`bash` with no `/c`/`-c`), so the shell's own exit code
    # doesn't reliably reflect whether the piped command actually failed —
    # on Windows in particular, a bare `cmd.exe` fed a command this way
    # exits 0 on natural EOF regardless of that command's own exit status.
    # This project's builds are expected to be entirely clean, so any
    # stderr output at all — not just lines that look like hard errors —
    # is treated as a failure.
    if returncode == 0 and error_lines:
        returncode = 1

    return returncode, error_lines

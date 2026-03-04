import sys
import os
import subprocess


if sys.platform.startswith('win'):
    SHELL = 'cmd'
else:
    SHELL = 'bash'


DUMMY_RETURN = b''


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

    while p.poll() is None:
        for line in iter(p.stdout.readline, DUMMY_RETURN):
            line = line.strip()
            if line:
                if sys.platform.startswith('win'):
                    sys.stdout.write(line.decode('utf-8') + '\n')
                else:
                    sys.stdout.write(line.decode('utf-8') + '\n')

                sys.stdout.flush()

        for line in iter(p.stderr.readline, DUMMY_RETURN):
            line = line.strip()
            if line:
                sys.stderr.write(line.decode('utf-8') + '\n')
                sys.stderr.flush()

    if not p.stdout.closed:
        p.stdout.close()

    if not p.stderr.closed:
        p.stderr.close()

    sys.stdout.flush()
    sys.stderr.flush()

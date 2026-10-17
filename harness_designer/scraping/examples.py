# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Example scripts for the script editor's Examples menu.

They teach one thing: how to write a script whose waits can be ended from
outside. Stop (SCRAPER_DESIGN.md, "Running scripts") raises an exception inside the
script's thread, which only works while the thread runs Python code; a thread
waiting in the operating system is out of its reach. The way out is to keep the
object the thread waits on -- a socket, an ``Event`` -- as an attribute of a
``threading.Thread`` subclass, so that a second script can find the thread with
``threading.enumerate()`` and end the wait on that object.

``exit_event`` and ``sock`` are the attribute names the examples agree on; the
"Release a stuck script" example looks for exactly those.
"""

from dataclasses import dataclass

from .. import check_types as _check_types

END_A_WAIT = 'end_a_wait'
WORKER_SOCKET = 'worker_socket'
PLAIN_SCRIPT = 'plain_script'
RELEASE_STUCK = 'release_stuck'


@dataclass(frozen=True)
class Example:
    """:ivar id: Stable key.
    :ivar title: The menu entry.
    :ivar summary: One sentence, for the menu's tool tip.
    :ivar code: The script.
    """

    id: str
    title: str
    summary: str
    code: str


_END_A_WAIT = r'''# Stop raises an exception inside this script's thread, but only while the thread
# is running Python code. A thread that is WAITING in the operating system --
# Event.wait(), Queue.get(), Thread.join(), time.sleep(), a socket read with no
# timeout -- is out of its reach, so Stop appears to do nothing.
#
# The remedy: keep the thing the thread waits on where somebody else can reach it,
# as an ATTRIBUTE of a threading.Thread subclass. Then a second script (Examples >
# Release a stuck script) can find the thread and end the wait from outside.
#
# Run this as it is and press Stop: it ends at once, because the loop at the bottom
# waits in short slices and Python code runs between them.
#
# To see a wait that Stop cannot end, set WAIT_FOR_EVER to True, run it, press Stop
# (a warning appears), and run "Release a stuck script". The Stop you pressed stays
# pending and takes effect the moment the wait is over.
import threading

WAIT_FOR_EVER = False


class Waiter(threading.Thread):
    """Does nothing until its exit_event is set."""

    def __init__(self):
        self.exit_event = threading.Event()      # what the thread waits on
        super().__init__(name='waiter', daemon=True)

    def run(self):
        self.exit_event.wait()
        print('waiter: the wait was ended')


waiter = Waiter()
waiter.start()
print('waiter started; press Stop to end the script')

try:
    if WAIT_FOR_EVER:
        waiter.join()                # a wait in the operating system: Stop cannot end it
    else:
        while waiter.is_alive():
            waiter.join(0.2)         # short slices: Stop can reach this loop
except BaseException:
    waiter.exit_event.set()          # Stop arrived: end the waiter's wait too
    raise

print('done')
'''

_WORKER_SOCKET = r'''# A download in a worker thread, whose network read can be ended from outside.
#
# Waiting for data on a socket is a wait in the operating system, which Stop cannot
# interrupt. Two things make it endable:
#   1. the worker keeps its socket (self.sock) and an Event (self.exit_event) as
#      attributes, so another script can find them; and
#   2. closing the socket from outside makes the blocked read fail at once.
#
# A timeout on the socket is the first defence, and it is here. This is for the time
# before the timeout runs out.
#
# Try it: point HOST and PORT at a server that accepts the connection and never
# answers, run it, press Stop, and when the warning appears run "Release a stuck
# script" from the Examples menu.
import socket
import threading

HOST = 'example.com'
PORT = 80
TIMEOUT = 60


class Download(threading.Thread):

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None                       # the connection, reachable from outside
        self.exit_event = threading.Event()    # set to ask the worker to finish
        self.data = b''
        self.error = None
        super().__init__(name='download', daemon=True)

    def run(self):
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=TIMEOUT)
            request = f'GET / HTTP/1.1\r\nHost: {self.host}\r\nConnection: close\r\n\r\n'
            self.sock.sendall(request.encode('ascii'))
            while not self.exit_event.is_set():
                chunk = self.sock.recv(65536)  # waits here until data arrives
                if not chunk:
                    break

                self.data += chunk
        except OSError as problem:
            if not self.exit_event.is_set():   # closing the socket from outside lands here too
                self.error = problem
        finally:
            if self.sock is not None:
                self.sock.close()

    def stop(self):
        """End the worker and whatever it is waiting for."""
        self.exit_event.set()
        sock = self.sock
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)  # wakes a blocked read on Linux and macOS
            except OSError:
                pass

            sock.close()                         # wakes it on Windows


worker = Download(HOST, PORT)
worker.start()
try:
    while worker.is_alive():
        worker.join(0.2)             # short slices: Stop can reach this loop
except BaseException:
    worker.stop()                    # Stop arrived: end the read as well
    raise

if worker.error is not None:
    raise worker.error

print(f'received {len(worker.data)} bytes')
'''

_PLAIN_SCRIPT = r'''# A script with no worker thread of its own.
#
# Harness Designer runs every script in a thread it made for it, and
# threading.current_thread() is that thread. An attribute put on it is as good as one
# on a Thread subclass: "Release a stuck script" finds it the same way.
#
# Try it: point HOST and PORT at a server that accepts the connection and never
# answers, run it, press Stop, and when the warning appears run "Release a stuck
# script" from the Examples menu.
import socket
import threading

HOST = 'example.com'
PORT = 80
TIMEOUT = 60

me = threading.current_thread()
me.sock = socket.create_connection((HOST, PORT), timeout=TIMEOUT)   # reachable from outside

me.sock.sendall(f'GET / HTTP/1.1\r\nHost: {HOST}\r\nConnection: close\r\n\r\n'.encode('ascii'))
data = b''
while True:
    chunk = me.sock.recv(65536)      # waits here until data arrives
    if not chunk:
        break

    data += chunk

me.sock.close()
print(f'received {len(data)} bytes')
'''

_RELEASE_STUCK = r'''# Run this while another script is stuck: you pressed Stop and nothing happened.
#
# It walks every thread in Harness Designer, shows which of them hold something they
# could be waiting on, and -- when you name one -- ends those waits from outside.
#
#   1. Run it as it is. It only LISTS the threads.
#   2. Put the name of the stuck thread in TARGET ('download', 'waiter', 'script-1',
#      ...) and run it again.
#
# It looks for the two attributes the other examples keep on their threads:
#   exit_event   a threading.Event   set() ends a wait on it
#   sock         a socket            shutdown() + close() ends a read on it
# A Queue would need a sentinel put() into it and a Lock would need release();
# add those below if your script uses them.
import socket
import threading

TARGET = ''


def release(thread):
    if hasattr(thread, 'exit_event'):
        thread.exit_event.set()
        print(f'  set {thread.name}.exit_event')

    if hasattr(thread, 'sock') and thread.sock is not None:
        try:
            thread.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

        thread.sock.close()
        print(f'  closed {thread.name}.sock')


me = threading.current_thread()
named = False
for thread in threading.enumerate():
    if thread is me or thread is threading.main_thread():
        continue

    holds = [name for name in ('exit_event', 'sock') if hasattr(thread, name)]
    print(f'{thread.name:<24} holds: {", ".join(holds) or "nothing"}')

    if TARGET and thread.name == TARGET:
        named = True
        release(thread)

if TARGET and not named:
    print(f'No thread is named {TARGET!r}.')
elif not TARGET:
    print('Nothing was released. Put a name from the list in TARGET and run again.')
'''

EXAMPLES: tuple[Example, ...] = (
    Example(END_A_WAIT, 'A wait that can be ended from outside',
            'A thread that waits on an Event kept as an attribute, and a loop Stop can reach.', _END_A_WAIT),
    Example(WORKER_SOCKET, 'A download whose network read can be ended',
            'A worker thread that keeps its socket as an attribute, so a blocked read can be cut.', _WORKER_SOCKET),
    Example(PLAIN_SCRIPT, 'A plain script with its socket on the thread',
            'No worker class: put the socket on threading.current_thread() instead.', _PLAIN_SCRIPT),
    Example(RELEASE_STUCK, 'Release a stuck script',
            'Run while another script is stuck: lists the threads and ends the waits of the one you name.',
            _RELEASE_STUCK),
)


@_check_types.do
def get(example_id: str) -> Example:
    """:raises KeyError: There is no such example."""
    for example in EXAMPLES:
        if example.id == example_id:
            return example

    raise KeyError(example_id)

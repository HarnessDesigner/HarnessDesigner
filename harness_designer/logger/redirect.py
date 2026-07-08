# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Redirects ``sys.stdout``/``sys.stderr`` into the logger, one line at a time.

``_StreamRedirector`` holds the io.TextIOWrapper plumbing that ``StdOut``
and ``StdErr`` would otherwise duplicate verbatim - buffering a partial
line until it sees '\\n', mirroring writes to the real console when one
exists, and the passthrough methods needed so code elsewhere still sees a
normal file-like object. Which real stream gets wrapped and which logger
method a completed line goes to is written directly in each subclass as a
plain, fixed call (``self._logger.info_block(text)`` /
``self._logger.error_block(text)``) - the ``Log`` instance is handed to
the constructor instead of looked up by import on every write, and the
method name is never resolved through getattr. Easy to trace by reading,
and something Cython can see and type at compile time.
"""

from typing import BinaryIO, Iterable, Iterator

import io
import sys


class _StreamRedirector(io.TextIOWrapper):
    """Shared TextIOWrapper plumbing for mirroring a std stream into the logger."""

    def __init__(self, original):
        self._original = original
        self._line = ''

        if original is not None:
            io.TextIOWrapper.__init__(self, original.buffer,
                                      encoding=original.encoding,
                                      errors=original.errors, newline=None,
                                      line_buffering=original.line_buffering,
                                      write_through=False)
        else:
            # No console attached (e.g. a --windowed build) - write() still
            # needs somewhere to hand data to io.TextIOWrapper.__init__.
            self._buffer = io.BytesIO()
            io.TextIOWrapper.__init__(self, self._buffer,
                                      encoding='utf-8',
                                      errors='backslashreplace', newline=None,
                                      line_buffering=False, write_through=False)

    def _log_line(self, text: str) -> None:
        """Overridden by StdOut/StdErr to call the matching logger function."""
        raise NotImplementedError

    # -- the actual redirection --------------------------------------------

    def write(self, s: str) -> int:
        if self._original is not None:
            try:
                self._original.write(s)
            except Exception:  # NOQA
                pass

        self._line += s
        if self._line.endswith('\n'):
            line, self._line = self._line, ''
            self._log_line(line)

        return len(s)

    def writelines(self, lines: Iterable[str]) -> None:
        lines = list(lines)
        if self._original is not None:
            try:
                self._original.writelines(lines)
            except Exception:  # NOQA
                pass

        for line in lines:
            if line.endswith('\n'):
                text = ''.join(lines)
                break
        else:
            text = '\n'.join(lines)

        self._log_line(text)

    def flush(self) -> None:
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:  # NOQA
                pass

        if self._line:
            line, self._line = self._line, ''
            self._log_line(line)

    # -- TextIOWrapper plumbing ---------------------------------------------
    # None of this touches the logger. It exists so code elsewhere that
    # expects a real file object (isatty(), context-manager use, iteration,
    # etc.) keeps working, by delegating to the real stream when there is
    # one and otherwise falling back to the in-memory buffer / a harmless
    # default.

    def close(self) -> None:
        if self._original is None:
            io.TextIOWrapper.close(self)
        else:
            self._original.close()

    def fileno(self) -> int:
        return -1 if self._original is None else self._original.fileno()

    def isatty(self) -> bool:
        return False if self._original is None else self._original.isatty()

    def readable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    def tell(self) -> int:
        return -1 if self._original is None else self._original.tell()

    def truncate(self, __size: int | None = None) -> int:
        return 0 if self._original is None else self._original.truncate(__size)

    def writable(self) -> bool:
        return True

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:  # NOQA
            pass

    def _checkClosed(self, msg: str | None = None) -> None:
        """No-op: keeps writes working even after the stream is flagged closed."""

    def detach(self) -> BinaryIO:
        return self._buffer if self._original is None else self._original.buffer

    def read(self, __size: int | None = 1) -> str:
        return '' if self._original is None else self._original.read(__size)

    @property
    def buffer(self) -> BinaryIO:
        return self._buffer if self._original is None else self._original.buffer

    @property
    def closed(self) -> bool:
        if self._original is None:
            return io.TextIOWrapper.closed.fget(self)
        return self._original.closed

    @property
    def write_through(self) -> bool:
        return False

    def reconfigure(self, **_kwargs) -> None:
        """No-op: nothing here honours stream reconfiguration requests."""

    def __enter__(self):
        if self._original is not None:
            self._original.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._original is not None:
            self._original.__exit__(exc_type, exc_val, exc_tb)

    def __iter__(self) -> Iterator[str]:
        return iter('') if self._original is None else self._original.__iter__()

    def __next__(self) -> str:
        if self._original is None:
            return io.TextIOWrapper.__next__(self)
        return self._original.__next__()

    def readline(self, __size: int = -1) -> str:
        return '' if self._original is None else self._original.readline(__size)

    def readlines(self, __hint: int = -1) -> list[str]:
        return [] if self._original is None else self._original.readlines(__hint)

    def seek(self, __cookie: int, __whence: int = 0) -> int:
        if self._original is None:
            return -1
        return self._original.seek(__cookie, __whence)


class StdOut(_StreamRedirector):
    """Mirrors :data:`sys.stdout`; completed lines are logged at INFO."""

    def __init__(self, logger):
        super().__init__(sys.stdout)
        self._logger = logger
        sys.stdout = self

    def _log_line(self, text: str) -> None:
        text = text.rstrip()
        if not text:
            return

        self._logger.info_block(text)


class StdErr(_StreamRedirector):
    """Mirrors :data:`sys.stderr`; completed lines are logged at ERROR."""

    def __init__(self, logger):
        super().__init__(sys.stderr)
        self._logger = logger
        sys.stderr = self

    def _log_line(self, text: str) -> None:
        text = text.rstrip()
        if not text:
            return

        self._logger.error_block(text)

from typing import BinaryIO, Iterator, Iterable

import sys
import io

from . import log_handler as _log_handler


class StdErr(io.TextIOWrapper):

    def __init__(self, logger):
        self.__logger = logger
        o_stderr = sys.stderr
        self.__original_stderr__ = o_stderr

        self._line = ''

        if o_stderr is not None:
            io.TextIOWrapper.__init__(self, o_stderr.buffer,
                                      encoding=o_stderr.encoding,
                                      errors=o_stderr.errors, newline=None,
                                      line_buffering=o_stderr.line_buffering,
                                      write_through=False)
        else:
            self.__buffer = io.BytesIO()
            io.TextIOWrapper.__init__(self, self.__buffer,
                                      encoding='utf-8',
                                      errors='backslashreplace', newline=None,
                                      line_buffering=False, write_through=False)

        sys.stderr = self

    def close(self) -> None:
        if self.__original_stderr__ is None:
            io.TextIOWrapper.close(self)
        else:
            self.__original_stderr__.close()

    def fileno(self) -> int:
        if self.__original_stderr__ is None:
            return -1
        else:
            return self.__original_stderr__.fileno()

    def flush(self) -> None:
        if self.__original_stderr__ is not None:
            self.__original_stderr__.flush()

        if self._line:
            line = self._line.rstrip()
            self._line = ''

            if line:
                log_entry = _log_handler.build_message(
                    _log_handler.INFO, (line,))

                self.__logger.log_handler.write(log_entry)

    def isatty(self) -> bool:
        if self.__original_stderr__ is None:
            return False
        else:
            return self.__original_stderr__.isatty()

    def readable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    def tell(self) -> int:
        if self.__original_stderr__ is None:
            return -1

        else:
            return self.__original_stderr__.tell()

    def truncate(self, __size: int | None = None) -> int:
        if self.__original_stderr__ is None:
            return 0
        else:
            return self.__original_stderr__.truncate(__size)

    def writable(self) -> bool:
        return True

    def __del__(self) -> None:
        try:
            self.close()
        except:  # NOQA
            pass

    def _checkClosed(self, msg: str | None = None) -> None:
        pass

    def detach(self) -> BinaryIO:
        if self.__original_stderr__ is None:
            return self.__buffer
        else:
            return self.__original_stderr__.buffer

    def write(self, __s: str) -> int:
        if self.__original_stderr__ is not None:
            self.__original_stderr__.write(__s)
        else:
            pass
            # io.TextIOWrapper.write(self, __s)

        self._line += __s
        if self._line.endswith('\n'):
            line = self._line.rstrip()
            self._line = ''
            if line:
                log_entry = _log_handler.build_message(
                    _log_handler.ERROR, (line,))

                self.__logger.log_handler.write(log_entry)

        return len(__s)

    def write_log(self, log_entry: dict):
        """Write a pre-built log entry (used by wx log redirection)"""
        if self.__original_stderr__ is not None:

            msg = (f"{log_entry['timestamp']} {log_entry['level']}: "
                   f"{log_entry['message']}\n")

            self.__original_stderr__.write(msg)

        self.__logger.log_handler.write(log_entry)

    def read(self, __size: int | None = 1) -> str:
        if self.__original_stderr__ is None:
            return ''
        else:
            return self.__original_stderr__.read(__size)

    @property
    def buffer(self) -> BinaryIO:
        if self.__original_stderr__ is None:
            return self.__buffer
        else:
            return self.__original_stderr__.buffer

    @property
    def closed(self) -> bool:
        if self.__original_stderr__ is None:
            return io.TextIOWrapper.closed.fget(self)
        else:
            return self.__original_stderr__.closed

    @property
    def write_through(self) -> bool:
        return False

    def reconfigure(
        self,
        *,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
        line_buffering: bool | None = None,
        write_through: bool | None = None,
    ) -> None:
        pass

    def __enter__(self):
        if self.__original_stderr__ is not None:
            self._context = self.__original_stderr__.__enter__()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__original_stderr__ is not None:
            self.__original_stderr__.__exit__(exc_type, exc_val, exc_tb)
            self._context = None

    def __iter__(self) -> Iterator[str]:
        if self.__original_stderr__ is None:
            return iter('')
        else:
            return self.__original_stderr__.__iter__()

    def __next__(self) -> str:
        if self.__original_stderr__ is None:
            return ''
        else:
            return self.__original_stderr__.__next__()

    def writelines(self, __lines: Iterable[str]) -> None:
        if self.__original_stderr__ is not None:
            self.__original_stderr__.writelines(__lines)

        for line in __lines:
            if line.endswith('\n'):
                __lines = ''.join(__lines)
                break
        else:
            __lines = '\n'.join(__lines)

        log_entry = _log_handler.build_message(
            _log_handler.ERROR, (__lines.rstrip(),))

        self.__logger.log_handler.write(log_entry)

    def readline(self, __size: int = -1) -> str:
        if self.__original_stderr__ is None:
            return ''
        else:
            return self.__original_stderr__.readline(__size)

    def readlines(self, __hint: int = -1) -> list[str]:
        if self.__original_stderr__ is None:
            return []
        else:
            self.__original_stderr__.readlines(__hint)

    def seek(self, __cookie: int, __whence: int = 0) -> int:
        if self.__original_stderr__ is None:
            return -1
        else:
            return self.__original_stderr__.seek(__cookie, __whence)

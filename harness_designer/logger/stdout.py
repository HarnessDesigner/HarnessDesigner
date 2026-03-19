from typing import Iterator, BinaryIO, Iterable

import sys

import io


class StdOut(io.TextIOWrapper):

    def __init__(self, logger):

        self.__logger = logger
        o_stdout = sys.stdout
        self.__original_stdout__ = o_stdout

        if o_stdout is not None:
            io.TextIOWrapper.__init__(self, o_stdout.buffer,
                                      encoding=o_stdout.encoding,
                                      errors=o_stdout.errors, newline=None,
                                      line_buffering=o_stdout.line_buffering,
                                      write_through=False)
        else:
            self.__buffer = io.BytesIO()
            io.TextIOWrapper.__init__(self, self.__buffer,
                                      encoding='utf-8',
                                      errors='backslashreplace', newline=None,
                                      line_buffering=False, write_through=False)

            sys._stdout = self

        sys.stdout = self

    def close(self) -> None:
        if self.__original_stdout__ is None:
            io.TextIOWrapper.close(self)
        else:
            self.__original_stdout__.close()

    def fileno(self) -> int:
        if self.__original_stdout__ is None:
            return io.TextIOWrapper.fileno(self)
        else:
            return self.__original_stdout__.fileno()

    def flush(self) -> None:
        if self.__original_stdout__ is not None:
            self.__original_stdout__.flush()

        self.__logger.flush()

    def isatty(self) -> bool:
        return False

    def readable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        if self.__original_stdout__ is None:
            return io.TextIOWrapper.tell(self)

        else:
            return self.__original_stdout__.tell()

    def truncate(self, __size: int | None = None) -> int:
        if self.__original_stdout__ is None:
            return io.TextIOWrapper.truncate(self, __size)
        else:
            return self.__original_stdout__.truncate(__size)

    def writable(self) -> bool:
        return True

    def __del__(self) -> None:
        pass

    def _checkClosed(self, msg: str | None = None) -> None:  # undocumented
        pass

    def detach(self) -> BinaryIO:
        pass

    def write(self, __s: str) -> int:
        if self.__original_stdout__ is not None:
            self.__original_stdout__.write(__s)

        self.__logger.info(__s.rstrip())

    def read(self, __size: int | None = 1) -> str:
        if self.__original_stdout__ is None:
            return io.TextIOBase.read(self, __size)
        else:
            return self.__original_stdout__.read(__size)

    @property
    def buffer(self) -> BinaryIO:
        if self.__original_stdout__ is None:
            return self.__buffer
        else:
            return self.__original_stdout__.buffer

    @property
    def closed(self) -> bool:
        if self.__original_stdout__ is None:
            return io.TextIOWrapper.closed.fget(self)
        else:
            return self.__original_stdout__.closed

    @property
    def line_buffering(self) -> bool:
        return False

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

    # These are inherited from TextIOBase, but must exist in the stub to satisfy mypy.
    def __enter__(self):
        if self.__original_stdout__ is None:
            self._context = io.TextIOWrapper.__enter__(self)
        else:
            self._context = self.__original_stdout__.__enter__()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__original_stdout__ is None:
            io.TextIOWrapper.__exit__(self, exc_type, exc_val, exc_tb)
            self._context = None
        else:
            self.__original_stdout__.__exit__(exc_type, exc_val, exc_tb)
            self._context = None

    def __iter__(self) -> Iterator[str]:
        if self.__original_stdout__ is None:
            return io.TextIOWrapper.__iter__(self)
        else:
            return self.__original_stdout__.__iter__()

    def __next__(self) -> str:
        if self.__original_stdout__ is None:
            return io.TextIOWrapper.__next__(self)
        else:
            return self.__original_stdout__.__next__()

    def writelines(self, __lines: Iterable[str]) -> None:
        if self.__original_stdout__ is not None:
            self.__original_stdout__.writelines(__lines)

        __lines = '\n'.join(__lines)
        self.__logger.info(__lines.rstrip())

    def readline(self, __size: int = -1) -> str:
        if self.__original_stdout__ is None:
            return io.TextIOWrapper.readline(self, __size)
        else:
            return self.__original_stdout__.readline(__size)

    def readlines(self, __hint: int = -1) -> list[str]:
        if self.__original_stdout__ is None:
            return io.TextIOWrapper.readlines(self, __hint)
        else:
            self.__original_stdout__.readlines(__hint)

    def seek(self, __cookie: int, __whence: int = 0) -> int:
        if self.__original_stdout__ is None:
            return io.TextIOWrapper.seek(self, __cookie, __whence)
        else:
            return self.__original_stdout__.seek(__cookie, __whence)

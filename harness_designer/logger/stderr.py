from typing import Iterator, BinaryIO, Iterable

import codecs
import sys

import io


class StdErr(io.TextIOWrapper):

    def __init__(self, logger):
        self.__logger = logger
        o_stderr = sys.stderr
        self.__original_stderr__ = o_stderr

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

            sys._stderr = self

        sys.stderr = self

    def close(self) -> None:
        if self.__original_stderr__ is None:
            io.TextIOWrapper.close(self)
        else:
            self.__original_stderr__.close()

    def fileno(self) -> int:
        if self.__original_stderr__ is None:
            return io.TextIOWrapper.fileno(self)
        else:
            return self.__original_stderr__.fileno()

    def flush(self) -> None:
        if self.__original_stderr__ is not None:
            self.__original_stderr__.flush()

        self.__logger.flush()

    def isatty(self) -> bool:
        return False

    def readable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        if self.__original_stderr__ is None:
            return io.TextIOWrapper.tell(self)

        else:
            return self.__original_stderr__.tell()

    def truncate(self, __size: int | None = None) -> int:
        if self.__original_stderr__ is None:
            return io.TextIOWrapper.truncate(self, __size)
        else:
            return self.__original_stderr__.truncate(__size)

    def writable(self) -> bool:
        return True

    def __del__(self) -> None:
        pass

    def _checkClosed(self, msg: str | None = None) -> None:  # undocumented
        pass

    def detach(self) -> BinaryIO:
        pass

    def write(self, __s: str) -> int:
        if self.__original_stderr__ is not None:
            self.__original_stderr__.write(__s)

        self.__logger.error(__s.rstrip())

    def read(self, __size: int | None = 1) -> str:
        if self.__original_stderr__ is None:
            return io.TextIOBase.read(self, __size)
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
        if self.__original_stderr__ is None:
            self._context = io.TextIOWrapper.__enter__(self)
        else:
            self._context = self.__original_stderr__.__enter__()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__original_stderr__ is None:
            io.TextIOWrapper.__exit__(self, exc_type, exc_val, exc_tb)
            self._context = None
        else:
            self.__original_stderr__.__exit__(exc_type, exc_val, exc_tb)
            self._context = None

    def __iter__(self) -> Iterator[str]:
        if self.__original_stderr__ is None:
            return io.TextIOWrapper.__iter__(self)
        else:
            return self.__original_stderr__.__iter__()

    def __next__(self) -> str:
        if self.__original_stderr__ is None:
            return io.TextIOWrapper.__next__(self)
        else:
            return self.__original_stderr__.__next__()

    def writelines(self, __lines: Iterable[str]) -> None:
        if self.__original_stderr__ is not None:
            self.__original_stderr__.writelines(__lines)

        __lines = '\n'.join(__lines)
        self.__logger.error(__lines.rstrip())

    def readline(self, __size: int = -1) -> str:
        if self.__original_stderr__ is None:
            return io.TextIOWrapper.readline(self, __size)
        else:
            return self.__original_stderr__.readline(__size)

    def readlines(self, __hint: int = -1) -> list[str]:
        if self.__original_stderr__ is None:
            return io.TextIOWrapper.readlines(self, __hint)
        else:
            self.__original_stderr__.readlines(__hint)

    def seek(self, __cookie: int, __whence: int = 0) -> int:
        if self.__original_stderr__ is None:
            return io.TextIOWrapper.seek(self, __cookie, __whence)
        else:
            return self.__original_stderr__.seek(__cookie, __whence)


if __name__ == '__main__':

    with sys.stderr as blah:
        print(blah == sys.stderr)
        print(type(blah))

        for item in dir(blah):
            print(item)

    # stderr = StdErr()

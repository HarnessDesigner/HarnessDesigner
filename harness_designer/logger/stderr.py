from typing import Iterator, BinaryIO, Iterable

import sys

import io


class StdErr(io.TextIOWrapper):

    def __init__(self, logger):
        self.__logger = logger
        o_stderr = sys.stderr
        self.__original_stderr__ = o_stderr

        io.TextIOWrapper.__init__(self, self.__original_stderr__.buffer,
                                  encoding=o_stderr.encoding,
                                  errors=o_stderr.errors, newline=None,
                                  line_buffering=o_stderr.line_buffering,
                                  write_through=False)

        sys.stderr = self

    def close(self) -> None:
        self.__original_stderr__.close()

    def fileno(self) -> int:
        return self.__original_stderr__.fileno()

    def flush(self) -> None:
        self.__original_stderr__.flush()

    def isatty(self) -> bool:
        return True

    def readable(self) -> bool:
        return self.__original_stderr__.readable()

    def seekable(self) -> bool:
        return self.__original_stderr__.seekable()

    def tell(self) -> int:
        return self.__original_stderr__.tell()

    def truncate(self, __size: int | None = None) -> int:
        return self.__original_stderr__.truncate(__size)

    def writable(self) -> bool:
        return self.__original_stderr__.writable()

    def __del__(self) -> None:
        pass

    def _checkClosed(self, msg: str | None = None) -> None:  # undocumented
        pass

    def detach(self) -> BinaryIO:
        pass

    def write(self, __s: str) -> int:
        self.__original_stderr__.write(__s)
        self.__logger.print_error(__s.rstrip())

    def read(self, __size: int | None = 1) -> str:
        self.__original_stderr__.read(__size)

    @property
    def buffer(self) -> BinaryIO:
        return self.__original_stderr__.buffer

    @property
    def closed(self) -> bool:
        return self.__original_stderr__.closed

    @property
    def line_buffering(self) -> bool:
        return self.__original_stderr__.line_buffering

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
        self._context = self.__original_stderr__.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__original_stderr__.__exit__(exc_type, exc_val, exc_tb)
        self._context = None

    def __iter__(self) -> Iterator[str]:
        return self.__original_stderr__.__iter__()

    def __next__(self) -> str:
        return self.__original_stderr__.__next__()

    def writelines(self, __lines: Iterable[str]) -> None:
        self.__original_stderr__.writelines(__lines)

        __lines = '\n'.join(__lines)
        self.__logger.print_error(__lines.rstrip())

    def readline(self, __size: int = -1) -> str:
        return self.__original_stderr__.readline(__size)

    def readlines(self, __hint: int = -1) -> list[str]:
        self.__original_stderr__.readlines(__hint)

    def seek(self, __cookie: int, __whence: int = 0) -> int:
        return self.__original_stderr__.seek(__cookie, __whence)


if __name__ == '__main__':

    with sys.stderr as blah:
        print(blah == sys.stderr)
        print(type(blah))

        for item in dir(blah):
            print(item)

    # stderr = StdErr()

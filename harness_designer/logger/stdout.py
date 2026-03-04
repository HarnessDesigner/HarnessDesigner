from typing import Iterator, BinaryIO, Iterable

import sys

import io


class StdOut(io.TextIOWrapper):

    def __init__(self, logger):

        self.__logger = logger
        o_stdout = sys.stdout
        self.__original_stdout__ = o_stdout

        io.TextIOWrapper.__init__(self, self.__original_stdout__.buffer,
                                  encoding=o_stdout.encoding,
                                  errors=o_stdout.errors, newline=None,
                                  line_buffering=o_stdout.line_buffering,
                                  write_through=False)

        sys.stdout = self

    def close(self) -> None:
        self.__original_stdout__.close()

    def fileno(self) -> int:
        return self.__original_stdout__.fileno()

    def flush(self) -> None:
        self.__original_stdout__.flush()

    def isatty(self) -> bool:
        return True

    def readable(self) -> bool:
        return self.__original_stdout__.readable()

    def seekable(self) -> bool:
        return self.__original_stdout__.seekable()

    def tell(self) -> int:
        return self.__original_stdout__.tell()

    def truncate(self, __size: int | None = None) -> int:
        return self.__original_stdout__.truncate(__size)

    def writable(self) -> bool:
        return self.__original_stdout__.writable()

    def __del__(self) -> None:
        pass

    def _checkClosed(self, msg: str | None = None) -> None:  # undocumented
        pass

    def detach(self) -> BinaryIO:
        pass

    def write(self, __s: str) -> int:
        self.__logger.write_info(__s)
        # self.__original_stdout__.write(__s)

    def read(self, __size: int | None = 1) -> str:
        self.__original_stdout__.read(__size)

    @property
    def buffer(self) -> BinaryIO:
        return self.__original_stdout__.buffer

    @property
    def closed(self) -> bool:
        return self.__original_stdout__.closed

    @property
    def line_buffering(self) -> bool:
        return self.__original_stdout__.line_buffering

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
        self._context = self.__original_stdout__.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__original_stdout__.__exit__(exc_type, exc_val, exc_tb)
        self._context = None

    def __iter__(self) -> Iterator[str]:
        return self.__original_stdout__.__iter__()

    def __next__(self) -> str:
        return self.__original_stdout__.__next__()

    def writelines(self, __lines: Iterable[str]) -> None:
        # self.__original_stdout__.writelines(__lines)
        for line in __lines:
            self.__logger.write_info(line)

    def readline(self, __size: int = -1) -> str:
        return self.__original_stdout__.readline(__size)

    def readlines(self, __hint: int = -1) -> list[str]:
        self.__original_stdout__.readlines(__hint)

    def seek(self, __cookie: int, __whence: int = 0) -> int:
        return self.__original_stdout__.seek(__cookie, __whence)

# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""``stderr`` redirection wrapper used by :mod:`harness_designer.logger`."""

from typing import BinaryIO, Iterator, Iterable

import sys
import io

from . import log_handler as _log_handler


class StdErr(io.TextIOWrapper):
    """Mirror :data:`sys.stderr` while forwarding writes to the logger.

    :param logger: Logger instance that receives generated log entries.
    :type logger: :class:`harness_designer.logger.log_handler.Log`
    """

    def __init__(self, logger):
        """Wrap the current :data:`sys.stderr` object.

        :param logger: Logger instance that receives generated log entries.
        :type logger: :class:`harness_designer.logger.log_handler.Log`
        """
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
        """Close the wrapped stream.

        :returns: ``None``.
        :rtype: None
        """
        if self.__original_stderr__ is None:
            io.TextIOWrapper.close(self)
        else:
            self.__original_stderr__.close()

    def fileno(self) -> int:
        """Return the file descriptor of the wrapped stream.

        :returns: Wrapped descriptor, or ``-1`` when no original stream exists.
        :rtype: int
        """
        if self.__original_stderr__ is None:
            return -1
        else:
            return self.__original_stderr__.fileno()

    def flush(self) -> None:
        """Flush the wrapped stream and any buffered partial log line.

        :returns: ``None``.
        :rtype: None
        """
        if self.__original_stderr__ is not None:
            try:
                self.__original_stderr__.flush()
            except Exception:  # NOQA
                pass

        if self._line:
            line = self._line.rstrip()
            self._line = ''

            if line:
                log_entry = _log_handler.build_message(
                    _log_handler.INFO, (line,))

                self.__logger.log_handler.write(log_entry)

    def isatty(self) -> bool:
        """Return whether the wrapped stream is attached to a terminal.

        :returns: ``True`` when the original stream reports a TTY.
        :rtype: bool
        """
        if self.__original_stderr__ is None:
            return False
        else:
            return self.__original_stderr__.isatty()

    def readable(self) -> bool:
        """Return whether the stream is readable.

        :returns: Always ``False``.
        :rtype: bool
        """
        return False

    def seekable(self) -> bool:
        """Return whether the stream is seekable.

        :returns: Always ``False``.
        :rtype: bool
        """
        return False

    def tell(self) -> int:
        """Return the current wrapped stream position.

        :returns: Current position or ``-1`` when no original stream exists.
        :rtype: int
        """
        if self.__original_stderr__ is None:
            return -1

        else:
            return self.__original_stderr__.tell()

    def truncate(self, __size: int | None = None) -> int:
        """Truncate the wrapped stream when supported.

        :param __size: Optional target size.
        :type __size: int | None
        :returns: Result from the wrapped stream, or ``0`` without one.
        :rtype: int
        """
        if self.__original_stderr__ is None:
            return 0
        else:
            return self.__original_stderr__.truncate(__size)

    def writable(self) -> bool:
        """Return whether the stream is writable.

        :returns: Always ``True``.
        :rtype: bool
        """
        return True

    def __del__(self) -> None:
        """Attempt to close the wrapped stream during finalization.

        :returns: ``None``.
        :rtype: None
        """
        try:
            self.close()
        except:  # NOQA
            pass

    def _checkClosed(self, msg: str | None = None) -> None:
        """Placeholder override for :class:`io.TextIOWrapper` internals.

        The required behavior for this override is UNKNOWN.

        :param msg: Optional error message from the caller.
        :type msg: str | None
        :returns: ``None``.
        :rtype: None
        """
        pass

    def detach(self) -> BinaryIO:
        """Return the underlying binary buffer.

        :returns: Internal buffer or wrapped stream buffer.
        :rtype: typing.BinaryIO
        """
        if self.__original_stderr__ is None:
            return self.__buffer
        else:
            return self.__original_stderr__.buffer

    def write(self, __s: str) -> int:
        """Write text to the wrapped stream and log complete lines.

        :param __s: Text to write.
        :type __s: str
        :returns: Number of characters written.
        :rtype: int
        """
        if self.__original_stderr__ is not None:
            try:
                self.__original_stderr__.write(__s)
            except Exception:  # NOQA
                pass

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
        """Read from the wrapped stream when available.

        :param __size: Maximum number of characters to read.
        :type __size: int | None
        :returns: Read text, or an empty string without an original stream.
        :rtype: str
        """
        if self.__original_stderr__ is None:
            return ''
        else:
            return self.__original_stderr__.read(__size)

    @property
    def buffer(self) -> BinaryIO:
        """Return the underlying binary buffer.

        :returns: Internal buffer or wrapped stream buffer.
        :rtype: typing.BinaryIO
        """
        if self.__original_stderr__ is None:
            return self.__buffer
        else:
            return self.__original_stderr__.buffer

    @property
    def closed(self) -> bool:
        """Return whether the wrapped stream is closed.

        :returns: Closed state of the internal or wrapped stream.
        :rtype: bool
        """
        if self.__original_stderr__ is None:
            return io.TextIOWrapper.closed.fget(self)
        else:
            return self.__original_stderr__.closed

    @property
    def write_through(self) -> bool:
        """Return the write-through flag exposed by the wrapper.

        :returns: Always ``False``.
        :rtype: bool
        """
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
        """Placeholder reconfiguration hook.

        The intended reconfiguration behavior is UNKNOWN.

        :param encoding: Requested text encoding.
        :type encoding: str | None
        :param errors: Requested error handling policy.
        :type errors: str | None
        :param newline: Requested newline handling mode.
        :type newline: str | None
        :param line_buffering: Requested line buffering mode.
        :type line_buffering: bool | None
        :param write_through: Requested write-through mode.
        :type write_through: bool | None
        :returns: ``None``.
        :rtype: None
        """
        pass

    def __enter__(self):
        """Enter the wrapped stream context.

        :returns: This wrapper instance.
        :rtype: :class:`StdErr`
        """
        if self.__original_stderr__ is not None:
            self._context = self.__original_stderr__.__enter__()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the wrapped stream context.

        :param exc_type: Exception type, if any.
        :type exc_type: type | None
        :param exc_val: Exception instance, if any.
        :type exc_val: BaseException | None
        :param exc_tb: Traceback object, if any.
        :type exc_tb: types.TracebackType | None
        :returns: ``None``.
        :rtype: None
        """
        if self.__original_stderr__ is not None:
            self.__original_stderr__.__exit__(exc_type, exc_val, exc_tb)
            self._context = None

    def __iter__(self) -> Iterator[str]:
        """Return an iterator over the wrapped stream.

        :returns: Wrapped iterator or an empty iterator.
        :rtype: typing.Iterator[str]
        """
        if self.__original_stderr__ is None:
            return iter('')
        else:
            return self.__original_stderr__.__iter__()

    def __next__(self) -> str:
        """Return the next line from the wrapped stream.

        :returns: Next line, or an empty string without an original stream.
        :rtype: str
        """
        if self.__original_stderr__ is None:
            return ''
        else:
            return self.__original_stderr__.__next__()

    def writelines(self, __lines: Iterable[str]) -> None:
        """Write multiple lines and log them as a single entry.

        :param __lines: Lines to write.
        :type __lines: typing.Iterable[str]
        :returns: ``None``.
        :rtype: None
        """
        if self.__original_stderr__ is not None:
            try:
                self.__original_stderr__.writelines(__lines)
            except Exception:  # NOQA
                pass

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
        """Read one line from the wrapped stream when available.

        :param __size: Maximum number of characters to read.
        :type __size: int
        :returns: Read line, or an empty string without an original stream.
        :rtype: str
        """
        if self.__original_stderr__ is None:
            return ''
        else:
            return self.__original_stderr__.readline(__size)

    def readlines(self, __hint: int = -1) -> list[str]:
        """Read all available lines from the wrapped stream.

        :param __hint: Optional size hint.
        :type __hint: int
        :returns: Lines read from the wrapped stream, or an empty list.
        :rtype: list[str]
        """
        if self.__original_stderr__ is None:
            return []
        else:
            self.__original_stderr__.readlines(__hint)

    def seek(self, __cookie: int, __whence: int = 0) -> int:
        """Seek within the wrapped stream when available.

        :param __cookie: Target offset.
        :type __cookie: int
        :param __whence: Reference point for the seek.
        :type __whence: int
        :returns: New position, or ``-1`` without an original stream.
        :rtype: int
        """
        if self.__original_stderr__ is None:
            return -1
        else:
            return self.__original_stderr__.seek(__cookie, __whence)

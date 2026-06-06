# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import ctypes
import multiprocessing
import _winapi
import sys
import os


multiprocessing.set_start_method('spawn')

from PySide6.QtWidgets import QApplication


app = QApplication.instance() or QApplication(sys.argv)

ntdll = ctypes.WinDLL('ntdll')

q = multiprocessing.Queue()
handle = q._reader._handle
source = _winapi.GetCurrentProcess()

# Simulate what the child does - open the parent process from the child's perspective
# The child opens the parent with PROCESS_DUP_HANDLE
parent_pid = os.getpid()
try:
    parent_handle = _winapi.OpenProcess(
        _winapi.PROCESS_DUP_HANDLE,
        False,
        parent_pid
    )
    print(f"OpenProcess succeeded: {parent_handle}")

    # Now duplicate from parent into current process with DUPLICATE_CLOSE_SOURCE
    # This is exactly what the child does
    try:
        new_handle = _winapi.DuplicateHandle(
            parent_handle,
            handle,
            source,
            0,
            False,
            _winapi.DUPLICATE_SAME_ACCESS | _winapi.DUPLICATE_CLOSE_SOURCE
        )
        print(
            f"DuplicateHandle with DUPLICATE_CLOSE_SOURCE succeeded: {new_handle}"
            )
    except PermissionError:
        status = ntdll.RtlGetLastNtStatus()
        print(f"NTSTATUS: {status & (2 ** 32 - 1):#010x}")
        print("DuplicateHandle with DUPLICATE_CLOSE_SOURCE failed")

except PermissionError:
    status = ntdll.RtlGetLastNtStatus()
    print(f"OpenProcess NTSTATUS: {status & (2 ** 32 - 1):#010x}")
    print("OpenProcess failed")
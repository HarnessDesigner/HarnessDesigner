
import os
import sys

import sys

_original_excepthook = sys.excepthook

def _patched_excepthook(exc_type, exc_value, exc_tb):
    import traceback
    print("UNHANDLED EXCEPTION:")
    traceback.print_exception(exc_type, exc_value, exc_tb)
    _original_excepthook(exc_type, exc_value, exc_tb)

sys.excepthook = _patched_excepthook

def excepthook(exc_type, exc_value, exc_tb):
    import traceback
    print("QT UNHANDLED EXCEPTION:", flush=True)
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

if __name__ == '__main__':
    import multiprocessing

    multiprocessing.set_start_method('spawn')

sys.path.insert(0, os.path.dirname(__file__))

import harness_designer


def main():
    harness_designer.__main__()


if __name__ == '__main__':
    main()

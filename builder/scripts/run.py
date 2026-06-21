# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
import sys
import traceback


_original_excepthook = sys.excepthook


def _excepthook(exc_type, exc_value, exc_tb):
    print("UNHANDLED EXCEPTION:")

    traceback.print_exception(exc_type, exc_value, exc_tb)

    _original_excepthook(exc_type, exc_value, exc_tb)


sys.excepthook = _excepthook


if __name__ == '__main__':
    import multiprocessing

    multiprocessing.set_start_method('spawn')

sys.path.insert(0, os.path.dirname(__file__))

import bootstrap  # NOQA
bootstrap.run()

import harness_designer  # NOQA


def main():
    harness_designer.__main__()


if __name__ == '__main__':
    main()


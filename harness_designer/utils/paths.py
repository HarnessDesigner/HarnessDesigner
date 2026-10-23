# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import multiprocessing
import sys
import os

from .. import check_types as _check_types


# The name PyCharm gives the worker process it builds "skeletons" (stub files)
# in: ``Process(name=...)`` in helpers/generator3/core.py, shared code, so the
# same on every platform. The worker imports every compiled module it finds in
# the project interpreter, which includes an installed copy of this package, so
# import-time code that touches state outside the process compares
# ``multiprocessing.current_process().name`` against this (``current_process()``
# describes only the calling process, so a worker running next to the real
# application can't trip it).
SKELETON_WORKER_NAME = 'Skeleton Generator Worker'


@_check_types.do
def get_appdata() -> str:
    """
    Return the ``harness_designer`` application-data directory, creating it if needed.

    :returns: Absolute path to the per-user application-data directory.
    :rtype: str
    """

    user_profile = os.path.expanduser('~')

    if sys.platform.startswith('win'):
        app_data = os.path.join('appdata', 'roaming', 'HarnessDesigner')
    else:
        app_data = '.HarnessDesigner'

    app_data = os.path.join(user_profile, app_data)

    # Several ``Config`` classes call this while they are being defined, so
    # it runs on every import -- including PyCharm's skeleton generator,
    # which must not create the folder as a side effect.
    in_skeleton_generator = multiprocessing.current_process().name == SKELETON_WORKER_NAME

    if not in_skeleton_generator and not os.path.exists(app_data):
        os.mkdir(app_data)

    return app_data


@_check_types.do
def get_documents() -> str:
    """
    Return the user's default documents directory.

    :returns: Absolute path to the documents directory.
    :rtype: str
    """

    documents = os.path.expanduser('~')

    if sys.platform.startswith('win'):
        documents = os.path.join(documents, 'documents')

    return documents

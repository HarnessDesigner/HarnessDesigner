# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import sys
import os


def get_appdata():
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
    if not os.path.exists(app_data):
        os.mkdir(app_data)

    return app_data


def get_documents():
    """
    Return the user's default documents directory.

    :returns: Absolute path to the documents directory.
    :rtype: str
    """

    documents = os.path.expanduser('~')

    if sys.platform.startswith('win'):
        documents = os.path.join(documents, 'documents')

    return documents

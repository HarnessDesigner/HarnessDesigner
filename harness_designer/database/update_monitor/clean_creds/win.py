"""Windows credential-cleanup helpers used by the update monitor."""

import keyring
from win32ctypes.pywin32.win32cred import CredEnumerate

def run():
    """Delete cached database credentials from the Windows credential store.

    :returns: ``None``.
    :rtype: None
    """
    res = CredEnumerate()

    for item in res:
        if item['UserName'] in ('db_type', 'sqlite_path'):
            service = item['TargetName'].split('@', 1)[-1]
            username = item['UserName']
            keyring.delete_password(service, username)

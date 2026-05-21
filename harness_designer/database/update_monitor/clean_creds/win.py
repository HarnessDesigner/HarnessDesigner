import keyring
from win32ctypes.pywin32.win32cred import CredEnumerate

def run():
    res = CredEnumerate()

    for item in res:
        if item['UserName'] in ('db_type', 'sqlite_path'):
            service = item['TargetName'].split('@', 1)[-1]
            username = item['UserName']
            keyring.delete_password(service, username)

## FILES

#### __init__.py

Picks the right platform module for credential-store cleanup — `from . import win as module` — since Windows is the only platform implemented today. A non-Windows run of whatever calls `clean_creds` would need this package extended first with a `mac.py`/`linux.py` sibling.

#### win.py

`run()` — Windows credential-store cleanup, used to remove stale/leftover credentials the keyring-backed HMAC handshake (see `process/manager.py`'s `CredManager`) may have left behind. Like the rest of `process/`, this file is deliberately excluded from `check_types.py`'s runtime type-checking decorator (see `process/MAP.md`) — don't add `@_check_types.do` here without checking with the user.

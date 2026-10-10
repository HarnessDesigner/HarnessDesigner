# harness_designer/process/clean_creds/win.py

## Line 9-21 (`run`) — enumerate and delete every matching Windows credential
Enumerates the whole Windows credential store and deletes each entry whose user name is one of the monitor keys. Called once when a `CredManager` is created in the parent (see `manager.md`). The store is small, so the enumeration is cheap.

**Typing (fixed in this pass):** `run` declares `-> None`.

## FILES

#### __init__.py

Package init for the multiprocessing support code: keyring-backed credential handling for out-of-process DB access, and the worker processes that do heavy DB/3D-model/image work off the main (GUI) process so the UI never blocks.

#### db_broker.py

The database connection broker used by the worker processes: `BaseConnector` defines the shared `execute`/`fetchall`/`commit`/`close` surface, with `MySQLConnector` and `SQLiteConnector` subclasses. The SQLite connector opens the same on-disk file the main process already has open in WAL mode (MEMORY.md "SQLite runs in WAL mode") — a second connection from another process is fine on a local disk, but not on a network share.

#### image_process.py

Image worker (`ProcessWorker`) that handles background image fetch/processing — datasheets, CAD thumbnails, part images — off the main process.

#### manager.py

`CredManager` does keyring-backed credential management for DB monitor processes, using an HMAC handshake to authenticate the worker process to the credential store without passing the raw secret around. `ProcessManager(threading.Thread)` supervises the worker process(es) from the main process. Dialogs raised from an exception caught on a background thread here must be marshaled onto the main Qt thread via `app.CallAfter` — this file is MEMORY.md's own reference pattern for that ("Never let exceptions propagate").

#### model_process.py

3D model processing worker: imports source CAD files (STEP/IGES via OCP, others via pyassimp), simplifies the mesh (pyfqmr), computes smooth + face normals, and saves the result as an uncompressed `.npy` file at `<model_dir>/<uuid[:2]>/<uuid>.npy` — only metadata (uuid, vertex_count, aabb, obb) goes to the DB. Defines `ModelException`/`ModelLoadError`, `ThreadWorker`, `ProcessWorker`. See CODEBASE_MAP.md's "3D rendering pipeline" section for how the saved file is later streamed into the GPU via `np.load(mmap_mode='r')`.

**Drift note:** CODEBASE_MAP.md's `process/` listing and MEMORY.md's check_types.py rollout entry both still name a `db_process.py` ("database worker process"). It does not exist on disk — confirmed deleted in commit `de93046` ("changes database row id's to be a UUID"), the same change that moved project-db row ids to UUIDs. Whatever it did is now presumably covered by `db_broker.py` directly; nothing currently imports a `db_process` module. A `multiprocessing.Lock`-typed parameter in that now-deleted file actually crashed the `check_types.py` checker (annotated as the factory function `multiprocessing.Lock` instead of the real class `multiprocessing.synchronize.Lock`), and the whole `process/` package — `manager.py`, `db_broker.py`, `image_process.py`, `model_process.py`, `clean_creds/` — is deliberately left undecorated with `@_check_types.do` on the user's explicit instruction ("I know all of that works properly"), not because of a lingering checker bug; don't add the decorator here without checking with the user first. Also worth knowing: `process/` imports none of the project-db or id-generation code (MEMORY.md "Project row-id collision safety") — this package does genuinely heavy DB/model/image I/O, but it never mints project row ids.

## FOLDERS

#### clean_creds/

Windows-only credential-store cleanup, dispatched from this package's credential handling (`CredManager` in `manager.py`) by OS. See `clean_creds/MAP.md`.

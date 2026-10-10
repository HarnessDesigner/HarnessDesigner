# harness_designer/utils/paths.py

## Line 9-45 (`get_appdata`, `get_documents`) — path lookups
`get_appdata` creates the application-data directory if it is missing, which is a filesystem check per call. Both are called on demand. Fine.

**Typing (fixed in this pass):** both return `str`.

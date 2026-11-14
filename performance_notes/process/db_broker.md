# harness_designer/process/db_broker.py

## Line 17-89 (`BaseConnector`) — thin wrapper over a DB-API connection and cursor
`execute`, `fetchall`, `commit` and `close` each forward to the wrapped cursor or connection. Every SQL call from the child processes goes through here, so the wrapper adds one Python call per statement. The database work dominates. Fine.

**Doc mismatch (flagged, not changed):** `execute` is documented as returning "the connector-specific cursor result", but it returns nothing. Callers that need rows call `fetchall`.

## Line 97-150 (`MySQLConnector.__init__`) — opens a connection on each construction
Reads many `Config.mysql` values and calls `mysql.connector.connect` once per connector. Constructed once per worker run (`connect_to_database`), so the cost is one connection per job batch. Fine.

## Line 158-171 (`SQLiteConnector.__init__`) — opens a SQLite file
One `sqlite3.connect` per construction. Fine.

## Line 174-197 (`connect_to_database`) — dispatches on the connector type
One comparison per call. Fine.

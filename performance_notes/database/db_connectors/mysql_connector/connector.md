# harness_designer/database/db_connectors/mysql_connector/connector.py

SQL calls in this module (AST count): 7.

## Functions that issue SQL inside a loop
Each iteration makes its own query. Batching these outside the loop is the first thing to measure.
- `SQLConnector._ensure_row_id_functions`.


Status: static read of the code only. Nothing here has been profiled.

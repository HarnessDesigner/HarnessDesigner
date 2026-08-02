# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""DDL for the MySQL-side row-id generation mechanism.

``next_project_row_id``/``next_global_row_id`` are the server-side
counterparts of ``id_generator.pack_project_row_id``/``pack_global_row_id``
-- see that module for the full explanation of the bit layout and why the
timestamp component is compared/bumped rather than trusted for raw
resolution.

Layout (must stay in sync with database/id_generator.py by hand -- MySQL
has no way to share the Python constants)::

    [ project_id : 24 ][ timestamp : 64 ][ reserved : 20 ][ version : 4 ][ user_id : 16 ]

``project_id``/``timestamp``/``version``/``user_id`` are 24/64/4/16 bits --
none of that fits in a single MySQL integer (BIGINT tops out at 64 bits), so
the 128-bit value is built as two 64-bit halves and concatenated:

* high 64 bits = ``project_id`` (top 24 bits) + the top 40 bits of ``timestamp``
* low 64 bits  = the bottom 24 bits of ``timestamp`` + reserved (always 0) +
  ``version`` + ``user_id``

``next_global_row_id`` is just ``next_project_row_id(0)`` -- global_db rows
use the identical layout with the project_id field zeroed, so there's only
one real implementation to keep correct.

Both functions serialize through the same named lock and the same
``row_id_state`` row, since they share one monotonic nanosecond source --
there is no need for project-scoped and global-scoped generation to be
ordered relative to each other, only for each to be strictly monotonic on
its own.

Each statement here is executed individually (not as one multi-statement
batch) so the semicolons inside a routine's BEGIN/END body don't need any
DELIMITER handling -- the driver sends each CREATE FUNCTION body as a single
query string.

NOTE: written against documented MySQL 8.0 syntax; has not been exercised
against a live server in this environment. Verify before relying on it in
production.
"""

ROW_ID_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS row_id_state (
        id TINYINT NOT NULL PRIMARY KEY,
        last_issued_ns BIGINT UNSIGNED NOT NULL
    )
    """,

    """
    INSERT IGNORE INTO row_id_state (id, last_issued_ns) VALUES (1, 0)
    """,

    "DROP FUNCTION IF EXISTS resolve_app_user_id",

    """
    CREATE FUNCTION resolve_app_user_id() RETURNS INT UNSIGNED
        READS SQL DATA
    BEGIN
        DECLARE v_user INT UNSIGNED DEFAULT 0;
        DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_user = 0;

        SELECT id INTO v_user FROM app_users WHERE mysql_account = CURRENT_USER() LIMIT 1;

        RETURN v_user & 0xFFFF;
    END
    """,

    "DROP FUNCTION IF EXISTS next_project_row_id",

    """
    CREATE FUNCTION next_project_row_id(p_project_id INT UNSIGNED) RETURNS BINARY(16)
        NOT DETERMINISTIC
        MODIFIES SQL DATA
    BEGIN
        DECLARE v_now BIGINT UNSIGNED;
        DECLARE v_last BIGINT UNSIGNED;
        DECLARE v_user BIGINT UNSIGNED;
        DECLARE v_high BIGINT UNSIGNED;
        DECLARE v_low BIGINT UNSIGNED;

        DO GET_LOCK('harness_designer_row_id', -1);

        SET v_now = CAST(UNIX_TIMESTAMP(NOW(6)) * 1000000000 AS UNSIGNED);

        SELECT last_issued_ns INTO v_last FROM row_id_state WHERE id = 1;

        IF v_now <= v_last THEN
            SET v_now = v_last + 1;
        END IF;

        UPDATE row_id_state SET last_issued_ns = v_now WHERE id = 1;
        SET v_user = resolve_app_user_id();

        DO RELEASE_LOCK('harness_designer_row_id');

        -- high 64 = project_id(24, masked defensively) in bits 63-40, then
        -- the top 40 bits of the 64-bit timestamp in bits 39-0.
        SET v_high = ((p_project_id & 0xFFFFFF) << 40) | (v_now >> 24);

        -- low 64 = the bottom 24 bits of timestamp in bits 63-40, then 20
        -- reserved bits (left as 0, never written), then version (4 bits,
        -- must match id_generator.FORMAT_VERSION) in bits 19-16, then
        -- user_id (16 bits) in bits 15-0.
        SET v_low = ((v_now & 0xFFFFFF) << 40) | (1 << 16) | (v_user & 0xFFFF);

        RETURN UNHEX(CONCAT(
            LPAD(HEX(v_high), 16, '0'),
            LPAD(HEX(v_low), 16, '0')
        ));
    END
    """,

    "DROP FUNCTION IF EXISTS next_global_row_id",

    """
    CREATE FUNCTION next_global_row_id() RETURNS BINARY(16)
        NOT DETERMINISTIC
        MODIFIES SQL DATA
    BEGIN
        RETURN next_project_row_id(0);
    END
    """,
]

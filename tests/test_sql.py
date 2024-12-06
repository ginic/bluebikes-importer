import sqlite3

import bluebikes.sql


def test_execute_sql_script(tmp_path):
    script = "SELECT 'Hello world!';"
    script_path = tmp_path / "test.sql"
    script_path.write_text(script)
    temp_db = tmp_path / "db.sqlite"
    with sqlite3.connect(temp_db) as connection:
        cursor = bluebikes.sql.execute_sql_script(connection, script_path)
        assert cursor.fetchone() == ("Hello world!",)

import sqlite3

import bluebikes.sql


def test_execute_sql_script(tmp_path):
    script = "CREATE TABLE test (input TEXT); INSERT INTO test (input) VALUES ('Hello world!');"
    script_path = tmp_path / "test.sql"
    script_path.write_text(script)
    temp_db = tmp_path / "db.sqlite"
    with sqlite3.connect(temp_db) as connection:
        bluebikes.sql.execute_sql_script(connection, script_path)
        results = list(connection.execute("SELECT * FROM test;"))
        assert len(results) == 1
        assert results[0] == ("Hello world!",)

import glob
import os

import pytest
import sqlite3

import bluebikes.insert
import bluebikes.sql


@pytest.fixture(scope="function")
def empty_test_db(tmp_path):
    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as conn:
        bluebikes.insert._create_db(conn)

    return db_path


def test_create_db(empty_test_db):
    assert empty_test_db.exists()


def test_evenly_distribute_csv_files_for_insert_by_total_size(csv_dir):
    distribution = (
        bluebikes.insert.evenly_distribute_csv_files_for_insert_by_total_size(
            2, csv_dir
        )
    )
    assert len(distribution) == 2
    assert len(distribution[0]) == 1
    assert len(distribution[1]) == 1


def test_insert_rows_from_list_of_csvs(empty_test_db, csv_dir):
    worker_assignments = (1, glob.glob(os.path.join(csv_dir, "*.csv")))
    bluebikes.insert.insert_rows_from_list_of_csvs(worker_assignments, empty_test_db)

    with sqlite3.connect(empty_test_db) as conn:
        conn.enable_load_extension(True)
        conn.load_extension("mod_spatialite")
        result = list(conn.execute("SELECT COUNT(*) FROM bluebikes"))
        assert result == [(2,)]
        geoms = list(
            conn.execute(
                "SELECT ST_AsText(start_point), ST_AsText(end_point) FROM bluebikes ORDER BY started_at"
            )
        )
        # Make sure spatial data is correcly managed
        assert geoms[0] == (
            "POINT(-71.119084 42.387995)",
            "POINT(-71.111075 42.373379)",
        )
        assert geoms[1] == (
            "POINT(-71.0564382089648 42.40672099242264)",
            "POINT(-71.04731440549585 42.403369462300134)",
        )

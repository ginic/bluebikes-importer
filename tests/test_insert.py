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
        bluebikes.insert._initialize_bluebikes_spatialite_database(conn)

    return db_path


def test_create_db(empty_test_db):
    # Check both the database file and tables were created
    assert empty_test_db.exists()
    with sqlite3.connect(empty_test_db) as conn:
        tables = list(
            conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND "
                "(name='bluebikes' OR "
                "name='stations' OR "
                "name='station_links') "
                "ORDER BY name;"
            )
        )
        assert tables[0] == ("bluebikes",)
        assert tables[1] == ("station_links")
        assert tables[2] == ("stations",)


def test_evenly_distribute_csv_files_for_insert_by_total_size(csv_dir):
    distribution = bluebikes.insert.evenly_distribute_csv_files_for_insert_by_total_size(2, csv_dir)
    assert len(distribution) == 2
    assert len(distribution[0]) == 1
    assert len(distribution[1]) == 1


def test_insert_rows_from_list_of_csvs(empty_test_db, csv_dir):
    worker_assignments = (1, glob.glob(os.path.join(csv_dir, "*.csv")))
    bluebikes.insert.insert_trips_from_list_of_csvs(worker_assignments, empty_test_db)

    with sqlite3.connect(empty_test_db) as conn:
        bluebikes.sql._enable_spatialite(conn)
        result = list(conn.execute("SELECT COUNT(*) FROM bluebikes"))
        assert result == [(2,)]
        # Query geometry points using snap to grid to fix precision
        geoms = list(
            conn.execute(
                "SELECT "
                "ST_AsText(ST_SnapToGrid(ST_Transform(start_point, 4326), 0.000001)), "
                "ST_AsText(ST_SnapToGrid(ST_Transform(end_point, 4326), 0.000001)) "
                "FROM bluebikes ORDER BY started_at"
            )
        )
        # Make sure spatial data is correcly managed
        assert geoms[0] == (
            "POINT(-71.119084 42.387995)",
            "POINT(-71.111075 42.373379)",
        )
        assert geoms[1] == (
            "POINT(-71.056438 42.406721)",
            "POINT(-71.047314 42.403369)",
        )


def test_insert_stations(empty_test_db, published_stations_dir):
    # stations from stations_published_dir (3) and overrides stations (8)
    bluebikes.insert._insert_stations(published_stations_dir, empty_test_db)

    with sqlite3.connect(empty_test_db) as conn:
        bluebikes.sql._enable_spatialite(conn)
        stations = list(conn.execute("SELECT * FROM stations;"))
        assert len(stations) == 8


def test_insert_station_links(empty_test_db):
    bluebikes.insert._insert_station_mapping_links(empty_test_db)

    with sqlite3.connect(empty_test_db) as conn:
        station_links = list(conn.execute("SELECT * FROM station_links;"))
        assert len(station_links) == 20

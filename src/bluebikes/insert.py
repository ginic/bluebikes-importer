import csv
import glob
import os
import re
import sqlite3
from datetime import datetime

import bluebikes.sql
import bluebikes.stations.published.process as bbstations

# extracts YYYYMM from file names
MONTH_YEAR_RE = r"(20[0-4]\d)(0[1-9]|1[0-2])"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
# bluebikes started including fractional time in 2024
DATE_FORMAT_WITH_MS = "%Y-%m-%d %H:%M:%S.%f"

DATABASE = "bluebike.sqlite"
BULK_INSERT_SIZE = 1000
DATABASE_LOCK_TIMEOUT = 1800  # 30 minutes

# Index for column where start and end lat and long points appear in CSVs
# These indexes are used through 202303 (March 2023)
START_LATITUDE_IDX_THRU_202303 = 5
START_LONGITUDE_IDX_THRU_202303 = 6
END_LATITUDE_IDX_THRU_202303 = 9
END_LONGITUDE_IDX_THRU_202303 = 10

# These indexes are used starting in 202304 (April 2023)
START_LATITUDE_IDX = 8
START_LONGITUDE_IDX = 9
END_LATITUDE_IDX = 10
END_LONGITUDE_IDX = 11


def get_well_known_text_point(longitude, latitude):
    """Returns the Well Known Text format for a Point to
    insert into the SpatiaLite database
    """
    return f"POINT({longitude} {latitude})"


def evenly_distribute_csv_files_for_insert_by_total_size(num_workers, data_dir):
    # find all CSV files and their sizes
    pattern = os.path.join(data_dir, "*tripdata.csv")
    files = [(file, os.path.getsize(file)) for file in glob.glob(pattern)]

    # sort files by size in descending order (optional but helps in distribution)
    files.sort(key=lambda x: x[1], reverse=True)

    # initialize distribution dictionary
    distribution = {i: [] for i in range(num_workers)}  # Each worker has an empty list of files
    workers = [{"id": i, "total_size": 0} for i in range(num_workers)]

    # distribute files uniformly across workers
    for file, size in files:
        # Find the worker with the minimum total size
        min_worker = min(workers, key=lambda x: x["total_size"])
        distribution[min_worker["id"]].append(file)  # Add only file path, not size
        min_worker["total_size"] += size

    return distribution


def insert_trips_from_list_of_csvs(worker_assignments, database=DATABASE):
    worker_number, files = worker_assignments
    memory_conn, cursor = _initialize_in_memory_database(worker_number)

    for f in files:
        _insert_trips_from_single_csv(f, cursor)

    _dump_memory_db_trips_to_file(memory_conn, database)
    memory_conn.close()


def print_csv_header(file):
    """
    Helper function to print the first line of a CSV file. Useful for schema debugging
    """
    with open(file, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar="|")
        for row in reader:
            print((file, row))
            return


def _insert_stations(station_file_directory, database=DATABASE):
    """
    Finds and normalizes CSVs containing station data in station_file_directory and inserts them into the stations
    table in the database.
    """
    # The number of stations is <2000, so inserting in
    # one go should be fine
    stations_df = bbstations.process_to_dataframe(station_file_directory)
    stations_df["geom_point"] = stations_df.apply(
        lambda x: get_well_known_text_point(x["Longitude"], x["Latitude"]), axis=1
    )

    with sqlite3.connect(database) as conn:
        bluebikes.sql._enable_spatialite(conn)
        cursor = conn.cursor()
        cursor.executemany(bluebikes.sql.stations_insert, stations_df.values.tolist())


def _insert_station_mapping_links(station_links_csv=None, database=DATABASE):
    """Inserts station mappings from a CSV file with the header:
    `correct_id,correct_name,correct_src_file,raw_id,raw_name,raw_src_file`

    If no CSV file is provided, the packaged station link mapping will be used.
    """
    with sqlite3.connect(database) as conn:
        links_df = bbstations.get_station_links_dataframe(station_links_csv)
        cursor = conn.cursor()
        # Insert explicit mappings
        cursor.executemany(bluebikes.sql.station_mapping_insert, links_df.values.tolist())


def _insert_trips_from_single_csv(file, cursor):
    year, month = re.findall(MONTH_YEAR_RE, file)[0]
    month_year = int("%s%s" % (year, month))

    with open(file, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        insert_count = 0
        passed_header_row = False
        data_to_insert = []
        for row in reader:
            if not passed_header_row:
                passed_header_row = True
                # ensure we skip the header row
                continue

            data_to_insert.append(row)
            insert_count += 1

            # newer records drop duration
            if 202304 <= month_year:
                date_fmt = DATE_FORMAT_WITH_MS if (202406 <= month_year) else DATE_FORMAT
                end_date = datetime.strptime(row[3], date_fmt)
                start_date = datetime.strptime(row[2], date_fmt)
                time_delta = end_date - start_date
                row.insert(2, time_delta.total_seconds())

            # Add source file name as first column
            row.insert(0, os.path.basename(file))

            if insert_count == BULK_INSERT_SIZE:
                _bulk_insert_trips_by_schema(data_to_insert, month_year, cursor)
                insert_count = 0
                data_to_insert = []

    # insert any outstanding records from the last batch
    _bulk_insert_trips_by_schema(data_to_insert, month_year, cursor)


def _bulk_insert_trips_by_schema(data_to_insert, month_year, cursor):
    if month_year <= 202004:
        insert_stmt = bluebikes.sql.bluebikes_insert_stmt_v0
    elif 202005 <= month_year <= 202303:
        insert_stmt = bluebikes.sql.bluebikes_insert_stmt_v1
    elif 202304 <= month_year:
        insert_stmt = bluebikes.sql.bluebikes_insert_stmt_v2
    else:
        return
    try:
        cursor.executemany(insert_stmt, data_to_insert)
    except Exception as e:
        print(e)


def _initialize_in_memory_database(worker_number):
    memory_conn = sqlite3.connect(":memory:", timeout=DATABASE_LOCK_TIMEOUT, isolation_level=None)
    _configure_sqlite_pragma(memory_conn, "memory")
    bluebikes.sql._initialize_spatialite(memory_conn)
    # Don't enable spatial lite on the in memory DBs,
    # it can cause a race condition on the database lock
    _create_bluebikes_table(memory_conn, is_skip_spatial=True)
    cursor = memory_conn.cursor()
    _seed_auto_increment(cursor, worker_number)
    return memory_conn, cursor


def _configure_sqlite_pragma(connection, journal_mode="WAL"):
    connection.execute("PRAGMA synchronous = OFF")
    connection.execute("PRAGMA journal_mode = %s" % journal_mode)
    connection.execute("PRAGMA busy_timeout = %s" % (DATABASE_LOCK_TIMEOUT * 1000))


def _seed_auto_increment(cursor, worker_number):
    """
    This insert will seed the auto-increment primary key at a value related to the worker number.
    This is required to avoid ID collisions when dumping the in-memory database into the file.
    It will be deleted immediately.
    """
    auto_increment_start_id = worker_number * 100000000
    cursor.execute(bluebikes.sql.bluebikes_id_insert, [auto_increment_start_id])
    cursor.execute("delete from bluebikes where rowid=?", [auto_increment_start_id])


def _dump_memory_db_trips_to_file(memory_conn, database=DATABASE):
    """
    Insert data from the in-memory table to the file-based table
    """
    file_conn = sqlite3.connect(database, timeout=DATABASE_LOCK_TIMEOUT, isolation_level=None)
    _configure_sqlite_pragma(file_conn)
    memory_conn.execute('ATTACH DATABASE "%s" AS filedb' % database)
    memory_conn.execute(bluebikes.sql.bluebikes_insert_add_points)
    memory_conn.execute("DETACH DATABASE filedb")
    memory_conn.commit()
    file_conn.close()


def _create_table(
    connection,
    drop_existing_table,
    create_new_table,
    enable_spatial_columns=None,
    add_spatial_index=None,
):
    """
    Convenience method for creating tables.
    If you'd also like to add spatial data columns and indices, pass well formed
    queries to `enable_spatial_columns` and `add_spatial_index`.
    """
    connection.executescript(drop_existing_table)
    connection.execute(create_new_table)
    if enable_spatial_columns:
        connection.execute(enable_spatial_columns)

    if add_spatial_index:
        connection.execute(add_spatial_index)


def _create_bluebikes_table(connection, is_skip_spatial=False):
    """
    Create the 'bluebikes' trip table, overwriting any existing table with the same name.
    You can choose to skip using SpatiaLite features.
    If you're using spatial features, the SpatiaLite extension
    should already be enabled in the connection.
    """
    if is_skip_spatial:
        _create_table(
            connection,
            bluebikes.sql.bluebikes_table_drop,
            bluebikes.sql.bluebikes_create,
        )
    else:
        _create_table(
            connection,
            bluebikes.sql.bluebikes_table_drop,
            bluebikes.sql.bluebikes_create,
            bluebikes.sql.bluebikes_enable_spatialite,
            None,
            # Spatial indexes make inserts very slow, so make sure they're needed
            # bluebikes.sql.bluebikes_add_spatial_indexes,
        )


def _create_stations_table(connection):
    """
    Create the 'stations' table, overwriting any existing table with the same name.
    The SpatiaLite extension should already be enabled in the connection.
    """
    _create_table(
        connection,
        bluebikes.sql.stations_table_drop,
        bluebikes.sql.stations_create,
        bluebikes.sql.stations_enable_spatialite,
        bluebikes.sql.stations_add_spatial_index,
    )


def _create_station_links_table(connection):
    """
    Create the 'station_links' table, overwriting any existing table with the same name.
    """
    _create_table(
        connection,
        bluebikes.sql.station_mapping_drop,
        bluebikes.sql.station_mapping_create,
    )


def _initialize_bluebikes_spatialite_database(connection, is_new_database=True):
    """Fully re-creates the entire database with SpatiaLite enabled,
    overwriting any existing 'bluebikes' trip or 'stations' tables
    """
    bluebikes.sql._initialize_spatialite(connection, is_new_database)
    _create_bluebikes_table(connection)
    _create_stations_table(connection)
    _create_station_links_table(connection)

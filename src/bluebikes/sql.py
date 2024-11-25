# Drop the bluebikes table from the main database, don't return an error if it doesn't exist
bluebikes_table_drop = "SELECT DropTable(NULL, 'bluebikes', True);"

bluebikes_create = """
CREATE TABLE bluebikes (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    src_file TEXT NOT NULL,
    tripduration INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    start_id INTEGER NOT NULL,
    start_station_name TEXT NOT NULL,
    start_lat REAL NOT NULL,
    start_lng REAL NOT NULL,
    end_id INTEGER NOT NULL,
    end_station_name TEXT NOT NULL,
    end_lat REAL NOT NULL,
    end_lng REAL NOT NULL,
    ride_id INTEGER NOT NULL,
    usertype TEXT NOT NULL,
    birth_year INTEGER,
    gender TEXT,
    rideable_type TEXT,
    postal_code TEXT
);
"""
# Create columns for storing start and end points as geographic points
# in https://epsg.io/4326
bluebikes_enable_spatialite = """
SELECT
    AddGeometryColumn('bluebikes', 'start_point', 4326, 'POINT', 'XY'),
    AddGeometryColumn('bluebikes', 'end_point', 4326, 'POINT', 'XY');
"""

# Create spatial indexes on the start and end point columns,
# so they are faster to search and compare
bluebikes_add_spatial_indexes = """
SELECT
    CreateSpatialIndex('bluebikes', 'start_point'),
    CreateSpatialIndex('bluebikes', 'end_point');
"""


# all records up to and including 202004-bluebikes-tripdata.csv
bluebikes_insert_stmt_v0 = """
INSERT INTO bluebikes (
    src_file,
    tripduration,
    started_at,
    ended_at,
    start_id,
    start_station_name,
    start_lat,
    start_lng,
    end_id,
    end_station_name,
    end_lat,
    end_lng,
    ride_id,
    usertype,
    birth_year,
    gender,
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?;
"""

# all records between 202005-bluebikes-tripdata.csv - 202303-bluebikes-tripdata.csv
bluebikes_insert_stmt_v1 = """
INSERT INTO bluebikes (
    src_file,
    tripduration,
    started_at,
    ended_at,
    start_id,
    start_station_name,
    start_lat,
    start_lng,
    end_id,
    end_station_name,
    end_lat,
    end_lng,
    ride_id,
    usertype,
    postal_code,
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?;
"""

# all records between 202304-bluebikes-tripdata.csv - 202403-bluebikes-tripdata.csv
bluebikes_insert_stmt_v2 = """
INSERT INTO bluebikes (
    src_file,
    ride_id,
    rideable_type,
    tripduration,
    started_at,
    ended_at,
    start_station_name,
    start_id,
    end_station_name,
    end_id,
    start_lat,
    start_lng,
    end_lat,
    end_lng,
    usertype,
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?;
"""

# id insert
bluebikes_id_insert = """
INSERT INTO bluebikes (
    id,
    src_file,
    tripduration,
    started_at,
    ended_at,
    start_id,
    start_station_name,
    start_lat,
    start_lng,
    end_id,
    end_station_name,
    end_lat,
    end_lng,
    ride_id,
    usertype
)
VALUES (?, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1);
"""

bluebikes_insert_add_points = """
INSERT INTO filedb.bluebikes SELECT
    id,
    src_file,
    tripduration,
    started_at,
    ended_at,
    start_id,
    start_station_name,
    start_lat,
    start_lng,
    end_id,
    end_station_name,
    end_lat,
    end_lng,
    ride_id,
    usertype,
    birth_year,
    gender,
    rideable_type,
    postal_code,
    ST_SETSRID(ST_MAKEPOINT (start_lng, start_lat), 4326) as start_point,
    ST_SETSRID(ST_MAKEPOINT (end_lng, end_lat), 4326) as end_point
FROM bluebikes;
"""

stations_table_drop = "SELECT DropTable(NULL, 'stations', True);"

stations_create = """
CREATE TABLE stations (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    raw_id TEXT NOT NULL,
    name TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    municipality TEXT NOT NULL,
    public BOOLEAN,
    number_of_docks INTEGER NOT NULL,
    src_file TEXT NOT NULL,
    UNIQUE(raw_id, src_file)
);
"""

stations_enable_spatialite = """
SELECT
    AddGeometryColumn('stations', 'geom_point', 4326, 'POINT', 'XY');
"""

stations_add_spatial_index = """
SELECT CreateSpatialIndex('stations', 'geom_point');
"""

stations_insert = """
INSERT INTO stations (
    raw_id,
    name,
    latitude,
    longitude,
    municipality,
    public,
    number_of_docks,
    src_file,
    geom_point

)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ST_PointFromText(?, 4326));
"""


def _initialize_spatialite(connection, is_new_database=True):
    """
    Initialize SpatiaLite and spatial metadata for the database.
    Only needs to be run once when the database is first created.
    """
    _enable_spatialite(connection)
    if is_new_database:
        connection.execute("SELECT InitSpatialMetaData();")


def _enable_spatialite(connection):
    """
    Enables SpatiaLite in the connected database. Needs to be run any time
    you want to use SpatiaLite.
    """
    connection.enable_load_extension(True)
    connection.load_extension("mod_spatialite")

table_drop = "DROP TABLE IF EXISTS bluebikes; "

table_create = """
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
table_enable_spatialite = """
SELECT
    AddGeometryColumn('bluebikes', 'start_point', 4326, 'POINT', 'XY'),
    AddGeometryColumn('bluebikes', 'end_point', 4326, 'POINT', 'XY');
"""

# Create spatial indexes on the start and end point columns,
# so they are faster to search and compare
table_add_spatial_indexes = """
SELECT
    CreateSpatialIndex('bluebikes', 'start_point'),
    CreateSpatialIndex('bluebikes', 'end_point');
"""


# all records up to and including 202004-bluebikes-tripdata.csv
insert_stmt_v0 = """
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
    start_point,
    end_point
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ST_PointFromText(?, 4326), ST_PointFromText(?, 4326));
"""

# all records between 202005-bluebikes-tripdata.csv - 202303-bluebikes-tripdata.csv
insert_stmt_v1 = """
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
    start_point,
    end_point
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ST_PointFromText(?, 4326), ST_PointFromText(?, 4326));
"""

# all records between 202304-bluebikes-tripdata.csv - 202403-bluebikes-tripdata.csv
insert_stmt_v2 = """
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
    start_point,
    end_point
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ST_PointFromText(?, 4326), ST_PointFromText(?, 4326));
"""

# id insert
id_insert = """
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

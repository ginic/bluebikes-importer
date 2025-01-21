/*Creates a table of Bluebikes stations with latitude, longitude points represented as geometric points in EPSG 3857.
*/

SELECT DropTable(NULL, 'stations', True);

CREATE TABLE stations (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    raw_id TEXT NOT NULL,
    name TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    municipality TEXT,
    public BOOLEAN,
    number_of_docks INTEGER,
    src_file TEXT NOT NULL,
    UNIQUE(raw_id, src_file),
    UNIQUE(raw_id, name)
);

SELECT
    AddGeometryColumn('stations', 'geom_point', 3857, 'POINT', 'XY');

SELECT CreateSpatialIndex('stations', 'geom_point');


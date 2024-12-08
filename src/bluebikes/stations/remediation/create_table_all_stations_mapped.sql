/*Shows how every possible station from the bluebikes trips would be mapped
for normalization.
*/
SELECT DropTable(NULL, 'all_trips_stations', True);
CREATE TABLE all_trips_stations (
	station_id TEXT,
	station_name TEXT,
	total_trips INTEGER NOT NULL,
    estimated_latitude FLOAT,
	estimated_longitude FLOAT,
    -- Normalized station information could be NULL for missing station data
    normalized_id TEXT,
    normalized_name TEXT,
    normalized_latitude FLOAT,
    normalized_longitude FLOAT
);

SELECT
    AddGeometryColumn('all_trips_stations', 'geom_estimated', 3857, 'POINT', 'XY'),
    AddGeometryColumn('all_trips_stations', 'normalized_geom_point', 3857, 'POINT', 'XY');

WITH
all_trips_stations AS ( -- Grab all possible stations and their locations from trips data
    SELECT
        start_id AS station_id,
        start_station_name AS station_name,
        start_point AS geom_point
    FROM bluebikes
    UNION
    SELECT
        end_id AS station_id,
        end_station_name AS station_name,
        end_point AS geom_point
    FROM bluebikes
),
estimated_stations AS ( -- Compute number of trips and estimate station locations
    SELECT
        station_id,
        station_name,
        COUNT(*) AS total_trips,
        ST_Transform(ST_Centroid(ST_Collect(geom_point)), 4326) AS geom_estimated
    FROM all_trips_stations
    GROUP BY station_id, station_name
),
remapped_stations AS ( -- Add in explicitly re-mapped stations
    SELECT
        e.station_id,
        e.station_name,
        e.total_trips,
    	ST_Y(e.geom_estimated) AS estimated_latitude,
		ST_X(e.geom_estimated) AS estimated_longitude,
        ST_Transform(e.geom_estimated, 3857) AS geom_estimated, -- convert back to SRID 3857 for storage
        -- This is the potential join key with stations
        -- There might be no correction, in which case fall back to use the original id
        COALESCE(station_links.correct_id, e.station_id) AS normalized_id
    FROM estimated_stations AS e
    LEFT JOIN station_links ON (
        e.station_id = station_links.raw_id
        AND e.station_name = station_links.raw_name
        )
)
INSERT INTO all_trips_stations (
	station_id,
	station_name,
	total_trips,
	estimated_latitude,
	estimated_longitude,
	geom_estimated,
	normalized_id,
	normalized_name,
	normalized_latitude,
	normalized_longitude,
	normalized_geom_point)
SELECT
	r.station_id AS station_id,
	r.station_name AS station_name,
	r.total_trips AS total_trips,
    r.estimated_latitude AS estimated_latitude,
	r.estimated_longitude AS estimated_longitude,
	r.geom_estimated AS geom_estimated, -- convert back to SRID 3857 for storage
    -- Normalized station information could be NULL for missing station data
    stations.raw_id AS normalized_id,
    stations.name AS normalized_name,
    stations.latitude AS normalized_latitude,
    stations.longitude AS normalized_longitude,
    stations.geom_point AS normalized_geom_point
FROM remapped_stations r
LEFT JOIN stations ON r.normalized_id = stations.raw_id;
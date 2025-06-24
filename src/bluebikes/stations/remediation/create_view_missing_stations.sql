/*Creates views (saved queries) that are useful for examining stations that appear in trips,
but are missing from the stations table and original s3 bucket CSV files.
*/

--Stations that appear in trips, but not station metadata files
DROP VIEW IF EXISTS missing_stations;
CREATE VIEW missing_stations AS
SELECT
    station_id,
    station_name,
	total_trips,
    estimated_latitude,
    estimated_longitude,
    geom_estimated
FROM all_trips_stations WHERE normalized_id IS NULL
ORDER BY total_trips DESC;

--Join missing metadata stations with nearby stations
DROP VIEW IF EXISTS missing_stations_resolution;
CREATE VIEW missing_stations_resolution AS
SELECT
	s1.station_id AS missing_station_id,
	s1.station_name AS missing_station_name,
    s1.total_trips AS total_trips,
	s1.estimated_latitude AS estimated_latitude,
	s1.estimated_longitude AS estimated_longitude,
	s2.raw_id AS nearby_station_id,
	s2.name AS nearby_station_name,
	s2.src_file AS nearby_station_src_file,
	s2.latitude AS nearby_station_latitude,
	s2.longitude AS nearby_station_longitude,
	Distance(s1.geom_estimated, s2.geom_point) AS distance_meters
FROM missing_stations s1
LEFT JOIN stations s2
WHERE distance_meters < 200
ORDER BY s1.total_trips DESC;
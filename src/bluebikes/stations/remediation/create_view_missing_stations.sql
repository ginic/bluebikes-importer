/*View with saved query to find stations that are in Bluebikes trips data, but not in
stations data. Latitude and longitude of the stations is estimated from
taking the centroid of their points in trips data.
*/
CREATE VIEW missing_stations AS
WITH all_stations AS (
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
    FROM bluebikes),
estimated_stations AS (
	SELECT
		station_id,
	    station_name,
	    COUNT(*) AS total_trips,
	    ST_Transform(ST_Centroid(ST_Collect(geom_point)), 4326) as geom_estimated
	FROM all_stations
	WHERE
	NOT EXISTS (
		SELECT
			raw_id,
			raw_name
		FROM station_links sl
		WHERE all_stations.station_id=sl.raw_id AND all_stations.station_name = sl.raw_name
	)
	GROUP BY station_id, station_name
)
SELECT
	station_id,
	station_name,
	total_trips,
	ST_X(geom_estimated) AS estimated_longitude,
	ST_Y(geom_estimated) AS estimated_latitude
FROM estimated_stations
ORDER BY total_trips DSC;

/*Creates a view joining normalized station information to trips data
*/
CREATE VIEW normalized_bluebikes AS
SELECT
	b.id as id,
	b.src_file as src_file,
	b.tripduration as tripduration,
	b.started_at as started_at,
	b.ended_at as ended_at,
	s1.raw_id as start_id,
	s1.name as start_station_name,
	s1.latitude as start_lat,
	s1.longitude as start_lng,
	s2.raw_id as end_id,
	s2.name as end_station_name,
	s2.latitude as end_lat,
	s2.longitude as end_lng,
	b.ride_id as ride_id,
	b.usertype as usertype,
	b.birth_year as birth_year,
	s1.geom_point as start_point,
	s2.geom_point as end_point
FROM bluebikes b
-- start station corrected
LEFT JOIN station_links links1 ON links1.raw_id = b.start_id AND links1.raw_name = b.start_station_name --
LEFT JOIN stations s1 ON s1.raw_id = links1.correct_id
-- end station corrected
LEFT JOIN station_links links2 ON links2.raw_id = b.end_id and links2.raw_name = b.end_station_name
LEFT JOIN stations s2 on s2.raw_id = links2.correct_id;

/*Creates a view (saved query) returning station pairs that are more than 200 meters apart,
but have the same station id. It is a useful way to check for station ids that
have been re-used over time for different stations.
*/
DROP VIEW IF EXISTS potential_station_duplicates_distant;
CREATE VIEW potential_station_duplicates_distant AS
SELECT
	s1.raw_id AS raw_id1,
	s1.name AS name1,
	s1.src_file AS src_file1,
	s1.latitude AS lat1,
	s1.longitude AS long1,
	s1.municipality AS m1,
	s2.raw_id AS raw_id2,
	s2.name AS name2,
	s2.src_file AS src_file2,
	s2.latitude AS lat2,
	s2.longitude AS long2,
	s2.municipality AS m2,
	Distance(s1.geom_point, s2.geom_point) AS distance_meters
FROM stations s1
LEFT JOIN stations s2
WHERE distance_meters > 200
AND s1.id <> s2.id AND s1.src_file <> s2.src_file --This clause probably doesn't do anything
AND s1.raw_id = s2.raw_id
ORDER BY raw_id1, distance_meters;
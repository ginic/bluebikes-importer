
/*This query returns station pairs that are more than 200 meters apart,
but have the same station id. It is a useful way to check for station ids that
have been re-used over time for different stations.
*/
SELECT
	s1.raw_id as raw_id1,
	s1.name as name1,
	s1.src_file as src_file1,
	s1.latitude as lat1,
	s1.longitude as long1,
	s1.municipality as m1,
	s2.raw_id as raw_id2,
	s2.name as name2,
	s2.src_file as src_file2,
	s2.latitude as lat2,
	s2.longitude as long2,
	s2.municipality as m2,
	Distance(s1.geom_point, s2.geom_point) AS distance_meters
FROM stations s1
LEFT JOIN stations s2
WHERE distance_meters > 200 AND s1.id <> s2.id AND s1.src_file <> s2.src_file
AND s1.raw_id = s2.raw_id
ORDER BY raw_id1, distance_meters;
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
FROM stations s1 --values from s1 will become the standard in the final table
LEFT JOIN stations s2 --values from s2 are potential duplicates that will either be ignored or remapped
WHERE distance_meters < 200 --stations that are about 0.12 miles close together 
AND s1.id <> s2.id --prevents comparing row with itself using the unique primary key that's created on inserts
AND (s1.src_file = 'current_bluebikes_stations.csv' --Prioritize current_bluebikes_stations.csv first
 OR (s1.src_file = 'Hubway_Stations_as_of_July_2017.csv' AND --2nd priority is Hubway_Statios_as_of_July_2017.csv
 		(s2.src_file = 'Hubway_Stations_as_of_July_2017.csv' --don't need to compare with current_bluebikes_stations.csv, those are captured in previous clause
 		OR s2.src_file = 'Hubway_Stations_2011_2016.csv' 
 		OR s2.src_file = 'previous_Hubway_Stations_as_of_July_2017.csv')
 	)
 OR (s1.src_file = 'previous_Hubway_Stations_as_of_July_2017.csv' -- 3rd priority is prev_Hubway_Stations_as_of_July_2017.csv 
 		AND (s2.src_file = 'previous_Hubway_Stations_as_of_July_2017.csv' OR 
 		s2.src_file = 'Hubway_Stations_2011_2016.csv') -- Last priority is Hubway_Stations_2011_2016.csv, which will never appear as src_file1
 	)
 )
ORDER BY raw_id1, distance_meters;
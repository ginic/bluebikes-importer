/* This query returns all pairs of station that are close to each other, less
than 200 meters apart. To keep the number of results down,each source file is only
compared with itself and earlier station source files.
*/
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
FROM stations s1 --values from s1 will become the standard in the final table
LEFT JOIN stations s2 --values from s2 are potential duplicates that will either be ignored or remapped
WHERE distance_meters < 200 --stations that are about 0.12 miles close together
AND s1.id <> s2.id --prevents comparing row with itself using the unique primary key

AND (
    --Prioritize matching current_bluebikes_stations.csv first
    (s1.src_file = 'current_bluebikes_stations.csv' AND s1.src_file <> s2.src_file)
    --2nd priority is Hubway_Stations_AS_of_July_2017.csv
    OR (s1.src_file = 'Hubway_Stations_AS_of_July_2017.csv'
        AND s2.src_file IN ('Hubway_Stations_AS_of_July_2017.csv',
                            'Hubway_Stations_2011_2016.csv',
                            'previous_Hubway_Stations_AS_of_July_2017.csv',
                            'missing_stations.csv')
        )
    -- 3rd priority is prev_Hubway_Stations_AS_of_July_2017.csv
    OR (s1.src_file = 'previous_Hubway_Stations_AS_of_July_2017.csv'
        AND s2.src_file IN ('previous_Hubway_Stations_AS_of_July_2017.csv',
                            'Hubway_Stations_2011_2016.csv',
                            'missing_data.csv')
        )
    -- LASt priority is missing_data.csv, which will never appear AS src_file1
    OR (s1.src_file = 'Hubway_Stations_2011_2016.csv' AND s2.src_file= 'missing_data.csv')
)
ORDER BY raw_id1, distance_meters;
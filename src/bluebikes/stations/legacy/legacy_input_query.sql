-- this stations query will return all distinct start and end stations
WITH all_stations AS (SELECT start_id           AS station_id,
                             start_station_name AS station_name,
                             start_lat          AS lat,
                             start_lng          AS lng,
                             rideable_type
                      FROM bluebikes
                      UNION
                      SELECT end_id           AS station_id,
                             end_station_name AS station_name,
                             end_lat          AS lat,
                             end_lng          AS lng,
                             rideable_type
                      FROM bluebikes)
SELECT station_id,
       station_name,
       lat,
       lng
FROM all_stations
WHERE station_id != ''
  AND (
    rideable_type != 'electric_bike'
        OR rideable_type is NULL
    )
GROUP BY 1,
         2,
         3,
         4
ORDER BY station_name
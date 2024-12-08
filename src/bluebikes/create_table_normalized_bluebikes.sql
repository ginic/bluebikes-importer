/*Creates a table of bluebikes trips between stations where all information about
the stations is known
*/

SELECT DropTable(NULL, 'normalized_bluebikes', True);
CREATE TABLE normalized_bluebikes (
    id INTEGER PRIMARY KEY,
    src_file TEXT NOT NULL,
    tripduration INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    start_id INTEGER NOT NULL,
    start_station_name TEXT NOT NULL,
    start_lat REAL NOT NULL,
    start_lng REAL NOT NULL,
    end_id INTEGER NOT NULL,
    end_station_name TEXT NOT NULL,
    end_lat REAL NOT NULL,
    end_lng REAL NOT NULL,
    ride_id INTEGER NOT NULL,
    usertype TEXT NOT NULL,
    rideable_type TEXT NOT NULL
);
SELECT
    AddGeometryColumn('normalized_bluebikes', 'start_point', 3857, 'POINT', 'XY'),
    AddGeometryColumn('normalized_bluebikes', 'end_point', 3857, 'POINT', 'XY');

INSERT INTO normalized_bluebikes(
    id,
    src_file,
    tripduration,
    started_at,
    ended_at,
    start_id,
    start_station_name,
    start_lat,
    start_lng,
    end_id,
    end_station_name,
    end_lat,
    end_lng,
    ride_id,
    usertype,
    rideable_type,
    start_point,
    end_point
)
SELECT
	b.id AS id,
	b.src_file AS src_file,
	b.tripduration AS tripduration,
	b.started_at AS started_at,
	b.ended_at AS ended_at,
	s1.raw_id AS start_id,
	s1.name AS start_station_name,
	s1.latitude AS start_lat,
	s1.longitude AS start_lng,
	s2.raw_id AS end_id,
	s2.name AS end_station_name,
	s2.latitude AS end_lat,
	s2.longitude AS end_lng,
	b.ride_id AS ride_id,
	CASE WHEN (b.usertype = 'casual' OR b.usertype = 'Customer') THEN 'casual'
		ELSE 'member' --'member' or 'Subscriber'
		END usertype,
	CASE
		WHEN b.rideable_type = 'electric_bike' THEN 'electric_bike'
		ELSE 'classic_bike'
		END ridable_type,
	s1.geom_point AS start_point,
	s2.geom_point AS end_point
FROM bluebikes b
-- start station corrected
JOIN station_links links1 ON links1.raw_id = b.start_id AND links1.raw_name = b.start_station_name --
JOIN stations s1 ON s1.raw_id = links1.correct_id
-- end station corrected
JOIN station_links links2 ON links2.raw_id = b.end_id and links2.raw_name = b.end_station_name
JOIN stations s2 on s2.raw_id = links2.correct_id;
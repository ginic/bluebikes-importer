# Published station processing tool

Published stations are contained in the following CSV files described in the formats below. This tool will unify them
all in a single table (csv).

### Example usage
```commandline
poetry run published_station_processing
```

### Published station files

Below is a list of the published station files with a snippet of headers and content. These files will be found in the
data folder after downloading from s3.

#### Hubway_Stations_2011_2016.csv

```text
Station,Station ID,Latitude,Longitude,Municipality,# of Docks
Fan Pier,A32000,42.35328743,-71.04438901,Boston,15
```

#### previous_Hubway_Stations_as_of_July_2017.csv

```text
Station ID,Station,Latitude,Longitude,Municipality,publiclyExposed,# of Docks
A32019,175 N Harvard St,42.363796,-71.129164,Boston,1,18
```

#### Hubway_Stations_as_of_July_2017

```text
"Number","Name","Latitude","Longitude","District","Public","Total docks"
"A32019","175 N Harvard St","42.363796","-71.129164","Boston","Yes","18"
```

#### current_bluebikes_stations.csv

```text
Last Updated:,12/5/2023,,,,,
Number,Name,Latitude,Longitude,District,Public,Total docks
K32015,1200 Beacon St,42.34414899,-71.11467361,Brookline,Yes,15
```


## Data sanitization
This tool performs some light sanitization to get all stations in the same format. It accomplishes this by migrating the `Public` field to a boolean True/False in addition to inferring null values for the field.

## Output schema

#### all_published_stations.csv
```text
Station ID,Name,Latitude,Longitude,Municipality,Public,# of Docks,File
K32015,1200 Beacon St,42.34414899,-71.11467361,Brookline,True,15,current_bluebikes_stations.csv
```

## Duplicate station resolution process
The Bluebikes station data format in the published station comma-separated values (CSV) files
has changed over time, which means that station information comes different sources
with different formats, station name conventions and unique identifiers.
This can make it challenging to track station usage over time and verify which station a Bluebikes trip
started or ended at. In general, there are two overlapping problems that arise:
- "Unique identifiers" (the "Station ID" or "Number" column in original CSV files) for stations are reused over time
	for stations that have different names and are not in the same location. These stations are clearly NOT the same,
	but have the same ids, which must be corrected by re-mapping the ids.
- A station's id changes, but its name and location are
- Station names and locations may change slightly over time, but the station id remains the same and inspecting
	the metadata shows that they are truly the same station. This is typically due to minor changes in the station name
	(for example, "175 N Harvard St" vs. "Harvard University Transportation Services - 175 North Harvard St") or
	changes in the precision of the latitude/longitude values in the original CSV files.
	In these cases, station information from the most recent CSV file is kept.


Some related things to keep in mind:
- Sometimes a station's location physically changes in the real world due to relocation, temporary winter stations or
	construction, so the latitude/longitude is updated, but the station's name and id are kept.
	In this case, the threshold for deciding when a station is "new" is unclear. If a station moves more than
	a half mile away, but the name and id are the same, is it still the same station?
	There is some grey area in station de-duplication.
- There is no explicit information available about when a station was in operation. If a station's id no
	longer appears in the trip data, we can infer that the station has been removed,
	but there's a possibility it may just not be used.

Conceptually, we resolve duplicate station ids by drawing a 200 meter (0.12 mile) radius around each
station with a unique identifier, using the location from the most recent CSV file if the id appears more than once.
Then we manually check two things for each station:
- Stations with *different ids within the 200 meter radius*: Which stations have different ids within that radius?
	Are those actually duplicates of the original station? Be careful to check that there are not actually two stations in the same area, which sometimes happy (e.g. there are several Bluebikes stations around South Station)
	If so, add them to 'station_mapping.csv', always pointing to the most recent CSV file as containing the correct station.
- Stations with *the same ids outside the 200 meter radius*: These are probably actually different stations.
	A station outside the radius could be mapped to another nearby station in 'station_mapping.csv', or it might need
	to have a new unique id created for it, which can be added to 'station_id_overrides.csv'

1. Use the main `download_bluebikes` to create a `stations` table in the `bluebike.sql` table.
	Doing this runs the `bluebikes.stations.published.process.process_to_dataframe` function to get the stations.
	In addition, it adds a `geom_point` column showing the station's location in the
	[EPSG 3857](https://epsg.io/3857) map projection, which allows station locations
	to be compared in meter units.
2. Query the `stations` table to find stations that are within 200 meters of each other (less than 0.12 miles apart),
	but have different station ids, names or lat/long values using `duplication_geom_query.sql`. Manually inspect
	the results of this query to find situations where the id is different, but these refer to the same station.
	Update the `station_mapping.csv` file accordingly, pointing old station mappings to the correct
	station id in the most recent CSV file. If the name is different, but the id is the same, these are assumed to be
	the same station and are automatically handled by `bluebikes.stations.published.process.process_to_dataframe`.


Some additional details of this station de-duplication process:
- Station information from more recent files is prioritized. Whenever possible, the station name, id
	and location will come from the latest `current_bluebikes_stations.csv`.
- We assume that `current_bluebikes_stations.csv` is correct. No duplicate station ids appear in that file and to the
	best of our knowledge, all the stations listed there are currently in use.
- We tried to consider the context of the surrounding area when deduplicating station ids.
	For example, if a station moved to the other side of a park, but stays within the park, we considered that to still be the "same" station.
	However, if a station moved less than 200 meters, but is at a different intersection across a busy street, then it's a "different" station.


### Station ID Conflict Resolution
We maintain two files to help resolve the problems with station ids described above.

#### station_mapping.csv
This file maps stations from older files to their correct station ids in more recent station files. It is used to create a view
that joins the Bluebikes trips to their correct stations by taking into account the date of the trip.

```text
correct_id,correct_name,correct_src_file,raw_id,raw_name,raw_src_file
A32013,Surface Rd at India St,current_bluebikes_stations.csv,D32025,Milk St at India St,previous_Hubway_Stations_as_of_July_2017.csv
A32019,175 N Harvard St,current_bluebikes_stations.csv,A32007,Harvard Real Estate - North Harvard St at Western Ave,previous_Hubway_Stations_as_of_July_2017.csv
A32051,Day Sq,current_bluebikes_stations.csv,A32027,Chelsea St at Saratoga St,Hubway_Stations_as_of_July_2017.csv
B32020,Burlington Ave at Brookline Ave,current_bluebikes_stations.csv,B32009,Overland St at Brookline Ave,previous_Hubway_Stations_as_of_July_2017.csv
```

#### station_id_overrides.csv
This file corrects instances when a station id was re-used for different stations by providing new unique ids for the older stations.
It uses the same columns and format as `current_bluebikes_stations.csv` (without the 'Last Updated' header).
These stations are added to the database during station table creation time, just like station CSV files from the s3 bucket.

```text
Number,Name,Latitude,Longitude,District,Public,Total docks
OVERRIDE00001,Ferry St at Pleasantview Ave,42.4091487775453,-71.0459768400506,Everett,1,15
OVERRIDE00002,Norman St at Kelvin St,42.4058117170059,-71.0670885072068,Everett,1,15
```

## Quick Guide to SQLite and SpatiaLite
TODO
- (SpatiaLite functions for working with geographic data)[https://www.gaia-gis.it/gaia-sins/spatialite-sql-5.1.0.html]

Useful tools for querying and visualizing SpatiaLite data:
- (DBeaver)[https://dbeaver.com] is a free, open source tool for working with databases. You can use it to interact with the database via graphical tools or write and run SQL queries.
- (QGIS)[https://qgis.org] is a free, open source GIS software. You can use it to [open and visualize SpatiaLite data as maps](https://docs.qgis.org/3.34/en/docs/user_manual/managing_data_source/opening_data.html#index-11).



### Enabling SpatiaLite in DBeaver
TODO
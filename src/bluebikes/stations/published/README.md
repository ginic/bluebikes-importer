# Published station processing tool

Published stations are contained in the following CSV files described in the formats below. This tool will unify them
all in a single table or CSV.

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

### Missing stations
There are station ids and names that appear in the Bluebikes trips data, but are
not listed in the published station files. These are listed in `missing_stations.csv`
with latitude and longitude values estimated from the centroid of points they appeared
with in the trip data. This was generated with a saved query available in
`src/bluebikes/stations/remediation/create_view_missing_stations.sql`.

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
    for stations that have different names and are not in the same location.
    These stations are clearly NOT the same, but have the same ids,
    which must be corrected by re-mapping the ids.
- The station id changes, but its name differs only in punctuation and the location is also similar.
    These are more than likely the same station. These must be corrected by re-mapping the ids.
- Station names and locations may change slightly over time, but the station id remains the same and inspecting
    the metadata shows that they are truly the same station. This is typically due to minor changes in the station name
    (for example, "175 N Harvard St" vs. "Harvard University Transportation Services - 175 North Harvard St") or
    changes in the precision of the latitude/longitude values in the original CSV files.
    In these cases, station information from the most recent stations CSV file is kept by joining on the station id.


Some related things to keep in mind:
- Sometimes a station's location physically changes in the real world due to relocation, temporary winter stations or
	construction, so the latitude/longitude is updated, but the station's name and id are kept.
	In this case, the threshold for deciding when a station is "new" is unclear. If a station moves more than
	a half mile away, but the name and id are the same, is it still the same station?
	There is some grey area in station de-duplication.
- There is no explicit information available about when a station was in operation. If a station's id no
	longer appears in the trip data, we can infer that the station has been removed,
	but there's a possibility it may just not be used.

Conceptually, we resolve duplicate stations by drawing a 200 meter (0.12 mile) radius around each
station with a unique identifier, using the location from the most recent CSV file if the id appears more than once.
Then we manually check three things by querying the database:
- Stations with *different ids within the 200 meter radius*: Which stations have different ids within that radius?
	Are those actually duplicates of the original station? Be careful to check that there are not actually two stations in the same area, which sometimes happy (e.g. there are several Bluebikes stations around South Station)
	If so, add them to 'station_mapping.csv', always pointing to the most recent CSV file as containing the correct station.
- Stations with *the same ids outside the 200 meter radius*: These are probably actually different stations.
	A station outside the radius could be mapped to another nearby station in 'station_mapping.csv', or it might need
	to have a new unique id created for it, which can be added to 'station_id_overrides.csv'
- Stations that appear in trips data, but are *missing from the original stations CSV files*:
    If the number of trips taken from these stations is high,
    these are real stations that just didn't appear in the s3 CSV files,
    and they can be added to 'station_id_overrides.csv' so their metadata is captured.
    If the number of trips is low (less than 10), then there are probably stations used for system testing and can be ignored.

You can check these by following this process
1. Use the main `download_bluebikes` to create a `stations` table and views (saved queries) for inspecting data in the `bluebike.sqlite` database.
    Doing this runs the `published_station_processing` script to populate the `stations` table.
    In addition, it adds a `geom_point` column showing the station's location in the
    [EPSG 3857](https://epsg.io/3857) map projection, which allows station locations
    to be compared in meter units.
2. Query the `stations` table to find stations that are within 200 meters of each other (less than 0.12 miles apart),
	but have different station ids, names or lat/long values using the `potential_station_duplicates_nearby` view created by `src/bluebikes/stations/remediation/create_view_nearby_duplicate_stations.sql`. Manually inspect
	the results of this query to find situations where the id is different, but these refer to the same station.
	Update the 'station_mapping.csv' file accordingly, pointing old station mappings to the correct
	station id in the most recent 'current_bluebikes_stations.csv' or 'station_id_overrides.csv'. If the name is different, but the id is the same, these are assumed to be
	the same station and are automatically handled by `bluebikes.stations.published.process.process_to_dataframe`.
3. Follow a similar process using the following views:
    - View `potential_station_duplicates_distant` (created by `src/bluebikes/stations/remediation/create_view_distant_duplicate_stations.sql`) checks distant stations with duplicate ids.
    - View `missing_stations` shows which stations appear in trips, but not station metadata.
        View `missing_stations_resolution` shows these missing station along with nearby stations as potential duplicates.
        Both views are created with `src/bluebikes/stations/remediation/create_view_missing_stations.sql`


Some additional details of this station de-duplication process:
- Station information from more recent files is prioritized. Whenever possible, the station name, id
    and location will come from the latest `current_bluebikes_stations.csv`.
- We assume that `current_bluebikes_stations.csv` is correct. No duplicate station ids
    appear in that file and to the best of our knowledge, all the stations listed there are currently in use.
- We tried to consider the context of the surrounding area when deduplicating station ids.
    For example, if a station moved to the other side of a park, but stays within the park,
    we considered that to still be the "same" station.
    However, if a station moved less than 200 meters, but is at a different intersection across a busy street, then it's a "different" station.
- There are a lot of stations extremely close to each other in the real world, so don't
    assume stations are duplicates just because they are close together.
    For example, there is a Bluebikes station in front of South Station and another directly across the street in Dewey Square,
    and there are several clustered around the Central Library and Copley Square.
    If can't visit the area, you can often use Google Streetview to verify if there are two Bluebikes stations nearby, but don't rely on Google's points of interest to find Bluebikes stations, because they are operating of the same flawed stations data.


### Station ID conflict resolution
We maintain two files to help resolve the problems with station ids described above.

#### station_mapping.csv
This file maps stations from older files to their correct station ids in more recent station files. It is used to create a view
that joins the stations from the original Bluebikes trips data ("raw" stations) to their "correct" stations.
Note that for this join to work the pair `(correct_id, correct_name)` cannot be the same as `(raw_id, raw_name)`.
At least one of the id or name should be different.

```text
correct_id,correct_name,correct_src_file,raw_id,raw_name,raw_src_file
A32013,Surface Rd at India St,current_bluebikes_stations.csv,D32025,Milk St at India St,previous_Hubway_Stations_as_of_July_2017.csv
A32019,175 N Harvard St,current_bluebikes_stations.csv,A32007,Harvard Real Estate - North Harvard St at Western Ave,previous_Hubway_Stations_as_of_July_2017.csv
A32051,Day Sq,current_bluebikes_stations.csv,A32027,Chelsea St at Saratoga St,Hubway_Stations_as_of_July_2017.csv
B32020,Burlington Ave at Brookline Ave,current_bluebikes_stations.csv,B32009,Overland St at Brookline Ave,previous_Hubway_Stations_as_of_July_2017.csv
OVERRIDE00001,Ferry St at Pleasantview Ave,station_id_overrides.csv,V32007,Ferry St at Pleasantview Ave,Hubway_Stations_as_of_July_2017.csv
```

#### station_id_overrides.csv
This file corrects instances when a station id was re-used for different stations by providing new unique ids for the older stations,
then adding an entry to station_mapping.csv.
It can also be used to add metadata for stations that exist and appear in trip data, but were not listed in any of the CSV files from the s3 bucket.
The station_id_overrides.csv file uses the same columns and format as `current_bluebikes_stations.csv` (without the 'Last Updated' header).
These stations are added to the database during station table creation time, with the published station CSV files from the s3 bucket.

```text
Number,Name,Latitude,Longitude,District,Public,Total docks
OVERRIDE00001,Ferry St at Pleasantview Ave,42.4091487775453,-71.0459768400506,Everett,1,15
OVERRIDE00002,Norman St at Kelvin St,42.4058117170059,-71.0670885072068,Everett,1,15
```


from bluebikes.stations.published.process import process_to_dataframe


def test_published_stations_from_csvs(published_stations_dir):
    all_published_stations_df = process_to_dataframe(
        published_stations_dir, is_include_station_overrides=False, is_include_missing_stations=False
    )
    all_published_stations = all_published_stations_df.to_dict(orient="list")
    expected_mappings = {
        "Station ID": ["K32015", "A32000", "A32019"],
        "Name": [
            "1200 Beacon St",
            "Fan Pier",
            "175 N Harvard St",
        ],
        "Latitude": [
            42.34414899,
            42.35328743,
            42.363796,
        ],
        "Longitude": [-71.11467361, -71.04438901, -71.129164],
        "Municipality": [
            "Brookline",
            "Boston",
            "Boston",
        ],
        "Public": [True, False, True],
        "# of Docks": [15, 15, 18],
        "File": [
            "current_bluebikes_stations.csv",
            "current_bluebikes_stations.csv",
            "Hubway_Stations_as_of_July_2017.csv",
        ],
    }

    assert all_published_stations == expected_mappings


def test_published_stations_from_csvs_keep_duplicates(published_stations_dir):
    all_published_stations_df = process_to_dataframe(
        published_stations_dir,
        drop_duplicates_across_files=False,
        is_include_station_overrides=False,
        is_include_missing_stations=False,
    )
    all_published_stations = all_published_stations_df.to_dict(orient="list")
    expected_mappings = {
        "Station ID": ["K32015", "A32000", "A32000", "A32019", "A32019"],
        "Name": [
            "1200 Beacon St",
            "Fan Pier",
            "Fan Pier",
            "175 N Harvard St",
            "175 N Harvard St",
        ],
        "Latitude": [42.34414899, 42.35328743, 42.35328743, 42.363796, 42.363796],
        "Longitude": [-71.11467361, -71.04438901, -71.04438901, -71.129164, -71.129164],
        "Municipality": ["Brookline", "Boston", "Boston", "Boston", "Boston"],
        "Public": [True, False, False, True, True],
        "# of Docks": [15, 15, 15, 18, 18],
        "File": [
            "current_bluebikes_stations.csv",
            "current_bluebikes_stations.csv",
            "Hubway_Stations_2011_2016.csv",
            "Hubway_Stations_as_of_July_2017.csv",
            "previous_Hubway_Stations_as_of_July_2017.csv",
        ],
    }

    assert all_published_stations == expected_mappings


def test_published_stations_overrides():
    station_overrides_df = process_to_dataframe(is_include_missing_stations=False)
    assert station_overrides_df.shape == (5, 8)

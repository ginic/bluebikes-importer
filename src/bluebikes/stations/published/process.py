import argparse
import importlib.resources
from pathlib import Path

import pandas as pd

DEFAULT_OUTPUT_FILE = "data/processed/all_published_stations.csv"

# Files we expect to download from Bluebikes S3 bucket
STATION_OVERRIDES_CSV = "station_id_overrides.csv"
STATIONS_CURRENT_CSV = "current_bluebikes_stations.csv"
STATIONS_2011_2016_CSV = "Hubway_Stations_2011_2016.csv"
STATIONS_HUBWAY_JULY_2017_CSV = "Hubway_Stations_as_of_July_2017.csv"
STATIONS_PREV_HUBWAY_JULY_2017_CSV = "previous_Hubway_Stations_as_of_July_2017.csv"


# Files we need to maintain in the repo
STATION_LINKS_MAPPING = "station_mapping.csv"
MISSING_STATIONS_CSV = "missing_stations.csv"

# Define the schema and names of the files to process
STATION_FILES = {
    STATIONS_CURRENT_CSV: {
        "usecols": [
            "Number",
            "Name",
            "Latitude",
            "Longitude",
            "District",
            "Public",
            "Total docks",
        ],
        "rename": {
            "Number": "Station ID",
            "District": "Municipality",
            "Total docks": "# of Docks",
        },
    },
    STATIONS_2011_2016_CSV: {
        "usecols": [
            "Station ID",
            "Station",
            "Latitude",
            "Longitude",
            "Municipality",
            "# of Docks",
        ],
        "rename": {"Station": "Name"},
        "default_public": None,
    },
    STATIONS_HUBWAY_JULY_2017_CSV: {
        "usecols": [
            "Number",
            "Name",
            "Latitude",
            "Longitude",
            "District",
            "Public",
            "Total docks",
        ],
        "rename": {
            "Number": "Station ID",
            "District": "Municipality",
            "Total docks": "# of Docks",
        },
    },
    STATIONS_PREV_HUBWAY_JULY_2017_CSV: {
        "usecols": [
            "Station ID",
            "Station",
            "Latitude",
            "Longitude",
            "Municipality",
            "publiclyExposed",
            "# of Docks",
        ],
        "rename": {"Station": "Name", "publiclyExposed": "Public"},
    },
    MISSING_STATIONS_CSV: {"usecols": ["Station ID", "Name", "Latitude", "Longitude"]},
}

# If there are duplicate ids in the stations, keep in this order of importance
# from most recent to oldest
STATION_SRC_PRIORITIES = [
    STATION_OVERRIDES_CSV,
    STATIONS_CURRENT_CSV,
    STATIONS_HUBWAY_JULY_2017_CSV,
    STATIONS_PREV_HUBWAY_JULY_2017_CSV,
    STATIONS_2011_2016_CSV,
    MISSING_STATIONS_CSV,
]

# These are the columns and their data types will appear in the final dataframe
# Note that technically str will be stored as an object dtype by pandas, but if you
# use the "string" example from the pandas docs, SQLite throws an error later
STATION_DTYPES = {
    "Latitude": float,
    "Longitude": float,
    "Public": bool,
    "# of Docks": int,
    "Station ID": str,
    "File": str,
    "Municipality": str,
    "Name": str,
}


# Function to fill NaNs with the mode
def fill_with_mode(series):
    if series.mode().empty:
        return series
    else:
        mode = series.mode()[0]
        return series.infer_objects(copy=False).fillna(mode)


def get_station_links_dataframe(link_csv_path=None):
    if link_csv_path is None:
        link_csv_path = importlib.resources.path("bluebikes.stations.published", STATION_LINKS_MAPPING)
    return pd.read_csv(link_csv_path, index_col=False)


def process_to_dataframe(
    station_file_directory=None,
    write_to_disk=None,
    simple_output=False,
    drop_duplicates_across_files=True,
    is_include_station_overrides=True,
    is_include_missing_stations=True,
):
    # Initialize an empty list to store dataframes
    dataframes = []

    station_csv_paths = []

    if is_include_station_overrides:
        station_csv_paths.append(importlib.resources.path("bluebikes.stations.published", STATION_OVERRIDES_CSV))

    if is_include_missing_stations:
        station_csv_paths.append(importlib.resources.path("bluebikes.stations.published", MISSING_STATIONS_CSV))

    if station_file_directory is not None:
        for file in STATION_FILES.keys():
            station_csv_paths.append(Path(station_file_directory) / file)

    # Read each file, rename columns, and append to list
    for file_path in station_csv_paths:
        file_name = file_path.name
        print("Parsing %s" % file_name)
        # Overrides are formatted like the current csv file
        if file_name == STATION_OVERRIDES_CSV:
            params = STATION_FILES[STATIONS_CURRENT_CSV]
        else:
            params = STATION_FILES[file_name]

        # skip the Last Updated row for the following file
        skip = 1 if file_name == "current_bluebikes_stations.csv" else 0
        df = pd.read_csv(file_path, skiprows=skip, usecols=params["usecols"])
        df.rename(columns=params["rename"], inplace=True)

        if "Public" in df.columns:
            df["Public"] = df["Public"].map({"Yes": True, "No": False, 1: True, 0: False})

        # Default to None for files that don't specify a public value
        # These will be filled with the most common value later
        if "default_public" in params:
            df["Public"] = params["default_public"]

        df["File"] = file_name
        dataframes.append(df)

    # Concatenate all dataframes
    combined_df = pd.concat(dataframes, ignore_index=True)

    # Apply the function to fill NaNs for 'Publicly Exposed'
    combined_df["Public"] = combined_df.groupby("Station ID")["Public"].transform(fill_with_mode)

    combined_df = combined_df.astype(STATION_DTYPES)
    print("Total station rows read from CSV files:", len(combined_df))

    if drop_duplicates_across_files:
        # Sort to keep current stations first
        sorting_map = {f: idx for idx, f in enumerate(STATION_SRC_PRIORITIES)}
        combined_df = combined_df.sort_values(by="File", key=lambda x: x.map(sorting_map))

        # Drop duplicate station ids, keep the ones specified by sort priority
        combined_df.drop_duplicates(subset=["Station ID"], inplace=True, keep="first")
        print("Total stations remaining after deduplication:", len(combined_df))

    if simple_output:
        combined_df.drop("Municipality", axis=1, inplace=True)
        combined_df.drop("Public", axis=1, inplace=True)
        combined_df.drop("# of Docks", axis=1, inplace=True)
        combined_df.drop("File", axis=1, inplace=True)

    if write_to_disk is not None:
        output_file = write_to_disk
        output_dir = Path(output_file)
        if not (output_dir.exists() and output_dir.is_dir()):
            print("Creating output directory: ", output_dir)
            output_dir.mkdir(parents=True)

        print("Writing to disk: ", output_file)
        with open(output_file, "w") as f:
            combined_df.to_csv(f, index=False)

    return combined_df


def main_cli():
    parser = argparse.ArgumentParser(
        description="""
        Tool to combine various published stations files into a single authoritative CSV file of all stations over time
    """
    )
    parser.add_argument(
        "directory",
        default="data/raw",
        nargs="?",  # make this single positional argument optional
        help="""
        Input CSV containing station facets from ride data
    """,
    )
    parser.add_argument(
        "-w",
        "--write-to-disk",
        default=DEFAULT_OUTPUT_FILE,
        help="Writes the results to disk",
    )
    parser.add_argument(
        "--simple-output",
        action="store_true",
        help="""
        Drops all columns except for id, name, lat, lng. Useful in conjunction with the legacy mapping tool
        """,
    )
    args = parser.parse_args()

    process_to_dataframe(args.directory, args.write_to_disk, args.simple_output)


if __name__ == "__main__":
    main_cli()

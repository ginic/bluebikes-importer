import argparse
import importlib.resources
import os
import sqlite3
import shutil

import bluebikes.insert as bbinsert
import bluebikes.download as bbdownload
import bluebikes.sql as bbsql

from tqdm.contrib.concurrent import process_map


def main_cli():
    parser = argparse.ArgumentParser(
        description="Download Blue Bikes data as CSV files, then load them into a SQLite Database called bluebike.sqlite"
    )
    parser.add_argument(
        "-d",
        "--data_dir",
        default="data/raw",
        help="A folder to store Blue Bikes CSV files downloaded from the S3 bucket. Defaults to 'data/raw'.",
    )
    parser.add_argument(
        "--no_cleanup",
        action="store_true",
        help="By default, the folder where CSV files will be deleted at the end."
        "Use this flag if you don't want to deleted them. This is useful for debugging purposes.",
    )
    parser.add_argument(
        "--download_only",
        action="store_true",
        help="Only download the files from S3, useful for layering within docker",
    )
    parser.add_argument(
        "--insert_only",
        action="store_true",
        help="Only attempt to insert records from files already download and re-create database helper tables and views. Will fail if no files are found in specified data_dir.",
    )
    parser.add_argument(
        "--postproc_only",
        action="store_true",
        help="Only run helper table and view creation, don't re-insert data from original S3 files",
    )
    parser.add_argument(
        "--num_procs",
        type=int,
        default=1,
        help="The number of workers used to process CSV files",
    )
    args = parser.parse_args()
    main(
        args.data_dir,
        not args.no_cleanup,
        args.download_only,
        args.insert_only,
        args.postproc_only,
        args.num_procs,
    )


def main(
    data_dir,
    is_cleanup_downloads=True,
    download_only=False,
    insert_only=False,
    postproc_only=False,
    worker_count=1,
):
    if insert_only or postproc_only:
        print("Running in no downloads mode. Skipping downloading of files from S3.")
    else:
        # create the temporary directory for storing the zip files and CSVs
        os.makedirs(data_dir, exist_ok=True)
        bbdownload.download_and_extract(worker_count, data_dir)

    if download_only or postproc_only:
        print("Running in no insert mode. Skipping inserting records from files.")
    else:
        # If the database already exists, you won't need to reinitialize SpatiaLite tables
        is_new_database = not os.path.exists(bbinsert.DATABASE)
        with sqlite3.connect(bbinsert.DATABASE, isolation_level=None) as db:
            print("==== Initializing SpatiaLite database ====")
            bbinsert._initialize_bluebikes_spatialite_database(db, is_new_database)

        print("==== Inserting station data ====")
        bbinsert._insert_stations(data_dir)

        print("==== Inserting bluebikes trips with %s workers ====" % worker_count)
        distribution = bbinsert.evenly_distribute_csv_files_for_insert_by_total_size(worker_count, data_dir)
        process_map(
            bbinsert.insert_trips_from_list_of_csvs,
            distribution.items(),
            [bbinsert.DATABASE] * len(distribution),
            max_workers=worker_count,
        )

    if not download_only:
        with sqlite3.connect(bbinsert.DATABASE) as db:
            bbsql._enable_spatialite(db)

            print("==== Inserting mapping for station normalization ====")
            bbinsert._create_station_links_table(db)
            db.commit()

            print("==== Creating view of fully normalized station mappings ====")
            bbsql.execute_sql_script(
                db,
                importlib.resources.path(
                    "bluebikes.stations.remediation",
                    "create_table_all_stations_mapped.sql",
                ),
            )
            db.commit()

            # Create an view for inspecting stations that appear in trips data, but not
            # station CSV files
            print("==== Creating views of stations with missing metadata ====")
            bbsql.execute_sql_script(
                db,
                importlib.resources.path("bluebikes.stations.remediation", "create_view_missing_stations.sql"),
            )
            db.commit()

            # Create table of normalized bluebikes trips
            print("==== Creating table with normalized Bluebikes trips ====")
            bbsql.execute_sql_script(
                db,
                importlib.resources.path("bluebikes", "create_table_normalized_bluebikes.sql"),
            )
            db.commit()

    # clean up all downloaded data to reduce the size of the docker image
    if is_cleanup_downloads and not (postproc_only or download_only):
        print("==== Removing downloaded files ====")
        shutil.rmtree(data_dir)


if __name__ == "__main__":
    main_cli()

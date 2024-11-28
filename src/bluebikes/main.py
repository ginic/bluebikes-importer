import argparse
import os
import sqlite3
import shutil

from bluebikes import insert
from bluebikes import download

from tqdm.contrib.concurrent import process_map


def main_cli():
    parser = argparse.ArgumentParser(
        description="Download Blue Bikes data as CSV files, then load them into a SQLite Database called bluebike.sqlite"
    )
    parser.add_argument(
        "-d",
        "--data_dir",
        default="data/raw",
        help="A folder to store Blue Bikes CSV files downloaded from the S3 bucket. Defaults to 'data'.",
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
        help="Only attempt to insert records from files already download. Will fail if no files are found",
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
        args.num_procs,
    )


def main(
    data_dir,
    is_cleanup_downloads=True,
    download_only=False,
    insert_only=False,
    worker_count=1,
):
    if insert_only:
        print("Running in insert_only mode. Skipping downloading of files from S3")
    else:
        # create the temporary directory for storing the zip files and CSVs
        os.makedirs(data_dir, exist_ok=True)
        download.download_and_extract(worker_count, data_dir)

    if download_only:
        print("Running in download_only mode. Skipping insert of files")
        return

    # If the database already exists, you won't need to reinitialize SpatiaLite tables
    is_new_database = not os.path.exists(insert.DATABASE)
    with sqlite3.connect(insert.DATABASE, isolation_level=None) as db:
        print("==== Initializing SpatiaLite database ====")
        insert._initialize_bluebikes_spatialite_database(db, is_new_database)

        # TODO Run queries that check for duplicate stations and print warnings

    print("==== Normalizing and inserting station data ====")
    insert._insert_stations(data_dir)

    print("==== Inserting bluebikes trips with %s workers ====" % worker_count)
    distribution = insert.evenly_distribute_csv_files_for_insert_by_total_size(worker_count, data_dir)
    process_map(
        insert.insert_trips_from_list_of_csvs,
        distribution.items(),
        [insert.DATABASE] * len(distribution),
        max_workers=worker_count,
    )

    # TODO Create views that join bluebikes trips to to the corrected station info to standarize station info appearing in trips

    # clean up all downloaded data to reduce the size of the docker image
    if is_cleanup_downloads:
        shutil.rmtree(data_dir)


if __name__ == "__main__":
    main_cli()

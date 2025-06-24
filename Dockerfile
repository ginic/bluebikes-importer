# Datasette base already has Spatialite dependencies
FROM datasetteproject/datasette:0.64.8 AS base

WORKDIR /usr/app
# Copy only the files for downloading and creating the database
COPY pyproject.toml README.md /usr/app/
COPY /src /usr/app/src

ENV BLUEBIKES_DB=/usr/app/bluebike.sqlite

# Install python dependencies
RUN pip install --no-cache-dir .

# Build a SQLite database on the image that can be viewed on datasette
FROM base AS bluebikes-importer-database
# Install datasette dependencies for GPS related visualizations
RUN datasette install datasette-cluster-map && \
    # Download the bluebike data from s3 and insert into SQLite
    download_bluebikes --database ${BLUEBIKES_DB}
# Use Datasette to serve the database on container startup
CMD ["sh", "-c" "datasette", "serve", "${BLUEBIKES_DB}", "--host", "0.0.0.0", "--port", "8001", "--setting", "sql_time_limit_ms", "60000", "--load-extension=spatialite"]

# Build the SQLite database dynamically when the image is run, so that you can
# choose a local mount point for the database
FROM base AS bluebikes-importer
CMD ["sh", "-c", "download_bluebikes", "--database", "${BLUEBIKES_DB}"]

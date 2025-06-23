FROM datasetteproject/datasette:0.64.8

WORKDIR /usr/app

# Copy only the files for downloading and creating the database
COPY pyproject.toml README.md /usr/app/
COPY /src /usr/app/src

ENV BLUEBIKES_DB=/usr/app/bluebike.sqlite

# Install python and datasette dependencies the cluster map for GPS related visualizations
RUN pip install --no-cache-dir . && \
    datasette install datasette-cluster-map

# Download the bluebike data from s3 and insert into SQLite
RUN download_bluebikes --database ${BLUEBIKES_DB}

# Use Datasette to serve the database on container startup
CMD ["datasette", "serve", "${BLUEBIKES_DB}", "--host", "0.0.0.0", "--port", "8001", "--setting", "sql_time_limit_ms", "60000", "--load-extension=spatialite"]

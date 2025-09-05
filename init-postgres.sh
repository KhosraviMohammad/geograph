#!/bin/bash
set -e

# Create additional database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE geograph_data;
EOSQL

# Create user and grant privileges
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER geograph WITH PASSWORD 'geograph' CREATEDB;
    GRANT ALL PRIVILEGES ON DATABASE geograph_layer TO geograph;
    GRANT ALL PRIVILEGES ON DATABASE geograph_data TO geograph;
EOSQL

# Enable PostGIS on geograph_layer
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "geograph_layer" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS postgis;
    CREATE EXTENSION IF NOT EXISTS postgis_topology;
    CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
    CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;
EOSQL

# Enable PostGIS on geograph_data
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "geograph_data" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS postgis;
    CREATE EXTENSION IF NOT EXISTS postgis_topology;
    CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
    CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;
EOSQL

# Grant schema permissions on geograph_data
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "geograph_data" <<-EOSQL
    GRANT ALL ON SCHEMA public TO geograph;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO geograph;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO geograph;
EOSQL

echo "PostgreSQL initialization completed successfully!"

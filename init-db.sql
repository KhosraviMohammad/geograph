-- Create databases for the geography project
-- This script runs when PostgreSQL container starts for the first time

-- Create geograph_layer database for GeoServer layers
CREATE DATABASE geograph_layer;

-- Create geograph_data database for Django application
CREATE DATABASE geograph_data;

-- Create user for both databases
-- User for both GeoServer layers and Django application
CREATE USER geograph WITH PASSWORD 'geograph';
GRANT ALL PRIVILEGES ON DATABASE geograph_layer TO geograph;
GRANT ALL PRIVILEGES ON DATABASE geograph_data TO geograph;

-- Grant additional privileges
ALTER USER geograph CREATEDB;

-- Connect to geograph_layer database and enable PostGIS
\c geograph_layer;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- Connect to geograph_data database and enable PostGIS
\c geograph_data;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

# Geography Project with GeoServer

This project contains a Django application with GeoServer for geospatial data management.

## Project Structure

```
geograph/
├── geograph/              # Django project
├── geography_env/         # Python virtual environment
├── docker-compose.yml     # GeoServer Docker setup
├── geoserver.env         # Environment variables
├── requirements.txt       # Python dependencies
└── manage.py             # Django management script
```

## Setup Instructions

### 1. Django Setup
```bash
# Activate virtual environment
source geography_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Django development server
python manage.py runserver
```

### 2. GeoServer Setup
```bash
# Start GeoServer with Docker Compose
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f geoserver
```

## Access Points

- **Django Admin**: http://localhost:8000/admin
- **GeoServer**: http://localhost:8080/geoserver
  - Username: admin
  - Password: geoserver
- **PostgreSQL**: localhost:5432
  - Admin: postgres/postgres
  - Both Databases: geograph/geograph
    - geograph_layer database (for GeoServer)
    - geograph_data database (for Django)

## PostGIS Features

Both databases include PostGIS extensions for geospatial data:
- **postgis**: Core spatial data types and functions
- **postgis_topology**: Topological data structures
- **fuzzystrmatch**: Fuzzy string matching for geocoding
- **postgis_tiger_geocoder**: US TIGER geocoding support

## Services

- **GeoServer**: Geospatial data server (Port 8080)
- **PostgreSQL with PostGIS**: Single database server (Port 5432)
  - **Layers Database**: `geograph_layer` (User: `geograph`) - with PostGIS extensions
  - **Django Database**: `geograph_data` (User: `geograph`) - with PostGIS extensions
  - **Admin User**: `postgres`
  - **PostGIS Extensions**: postgis, postgis_topology, fuzzystrmatch, postgis_tiger_geocoder

## Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f

# Remove all containers and volumes
docker-compose down -v
```

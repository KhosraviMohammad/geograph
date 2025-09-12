# Shapefile Import Fix for MultiPolygon Geometries

## Problem
The original shapefile import was failing with the error:
```
ERROR 1: COPY statement failed.
ERROR:  Geometry type (MultiPolygon) does not match column type (Polygon)
```

This occurred because the `ogr2ogr` command was creating tables with fixed geometry types (Polygon) but the shapefiles contained MultiPolygon geometries.

## Solution

### 1. Dynamic Geometry Type Detection
- Added `_detect_geometry_type()` method that uses `ogrinfo` to detect the actual geometry type of the shapefile
- Normalizes geometry types to promote single geometries to multi geometries for consistency

### 2. Flexible Import Strategy
- Primary approach: Uses `PROMOTE_TO_MULTI` flag to automatically promote single geometries to multi geometries
- Fallback approach: Uses generic `GEOMETRY` type if the primary approach fails

### 3. Enhanced ogr2ogr Command
```bash
ogr2ogr -f PostgreSQL "PG:host=... dbname=geograph_layer ..." shapefile.shp \
    -nln table_name \
    -overwrite \
    -lco GEOMETRY_NAME=geom \
    -lco FID=gid \
    -nlt PROMOTE_TO_MULTI \
    -lco SPATIAL_INDEX=GIST \
    -lco PRECISION=NO \
    -t_srs EPSG:4326
```

### 4. Fallback Method
If the primary import fails, the system automatically tries with:
```bash
ogr2ogr ... -nlt GEOMETRY ...
```

This uses the generic `GEOMETRY` type which accepts any geometry type (Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon, etc.).

## Key Features

### Geometry Type Detection
- Automatically detects geometry type using `ogrinfo`
- Promotes single geometries to multi geometries for consistency
- Handles all common geometry types

### Robust Error Handling
- Primary import attempt with `PROMOTE_TO_MULTI`
- Automatic fallback to `GEOMETRY` type if needed
- Detailed error messages and status tracking

### Enhanced Table Information
- Shows actual geometry type in database
- Displays SRID (Spatial Reference System ID)
- Provides column information and row counts

## Usage

The fix is automatically applied when uploading shapefiles through the API:

1. Upload a ZIP file containing shapefile components
2. System detects geometry type automatically
3. Creates table with appropriate geometry type
4. Falls back to generic GEOMETRY type if needed
5. Provides detailed information about the created table

## Supported Geometry Types

- **Point** → Promoted to MultiPoint
- **LineString** → Promoted to MultiLineString  
- **Polygon** → Promoted to MultiPolygon
- **MultiPoint** → Used as-is
- **MultiLineString** → Used as-is
- **MultiPolygon** → Used as-is
- **Any other type** → Uses generic GEOMETRY type

## Database Schema

Tables are created in the `geograph_layer` database with:
- `gid` - Primary key (auto-increment)
- `geom` - Geometry column (flexible type)
- Attribute columns from the shapefile
- Spatial index on geometry column

## Testing

Run the test script to verify the functionality:
```bash
cd geograph
python test_shapefile_import.py
```

## Dependencies

- GDAL/OGR tools (`ogr2ogr`, `ogrinfo`)
- PostgreSQL with PostGIS extension
- Django with GeoDjango support

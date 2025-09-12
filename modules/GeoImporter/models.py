from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import GEOSGeometry
import os
import tempfile
from django.conf import settings
from django.db import connections
import subprocess

class ShapefileImport(models.Model):
    """Model to track shapefile imports"""
    name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    table_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default='pending')
    
    def __str__(self):
        return f"{self.name} - {self.table_name}"
    
    def import_shapefile(self, shapefile_path):
        """Import shapefile and create dynamic table in datastore database"""
        try:
            # Generate unique table name
            import uuid
            self.table_name = f"shapefile_{uuid.uuid4().hex[:8]}"
            
            # Use ogr2ogr to import shapefile to PostgreSQL
            datastore_config = settings.DATABASES['datastore']
            
            # Build connection string
            conn_str = f"PG:host={datastore_config['HOST']} port={datastore_config['PORT']} dbname={datastore_config['NAME']} user={datastore_config['USER']} password={datastore_config['PASSWORD']}"
            
            # First, get geometry type information
            geometry_type = self._detect_geometry_type(shapefile_path)
            
            # ogr2ogr command with dynamic geometry type handling
            cmd = [
                'ogr2ogr',
                '-f', 'PostgreSQL',
                conn_str,
                shapefile_path,
                '-nln', self.table_name,
                '-overwrite',
                '-lco', 'GEOMETRY_NAME=geom',
                '-lco', 'FID=gid',
                '-nlt', 'PROMOTE_TO_MULTI',  # Promote single geometries to multi
                '-lco', 'SPATIAL_INDEX=GIST',  # Add spatial index
                '-lco', 'PRECISION=NO',  # Don't round coordinates
                '-t_srs', 'EPSG:4326'  # Ensure WGS84 projection
            ]
            
            # Execute ogr2ogr
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.status = 'success'
                self.save()
                return True, f"Shapefile imported successfully. Geometry type: {geometry_type}"
            else:
                # If first attempt fails, try with GEOMETRY type (most flexible)
                return self._import_with_geometry_type(shapefile_path, conn_str, geometry_type)
                
        except Exception as e:
            self.status = 'error'
            self.save()
            return False, f"Exception during import: {str(e)}"
    
    def _detect_geometry_type(self, shapefile_path):
        """Detect geometry type of shapefile using ogrinfo"""
        try:
            cmd = ['ogrinfo', '-so', shapefile_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse output to find geometry type
                for line in result.stdout.split('\n'):
                    if 'Geometry:' in line:
                        geom_type = line.split('Geometry:')[1].strip()
                        # Normalize geometry type names
                        if 'Multi' in geom_type:
                            return geom_type
                        elif 'Polygon' in geom_type:
                            return 'MultiPolygon'  # Promote to MultiPolygon
                        elif 'LineString' in geom_type:
                            return 'MultiLineString'  # Promote to MultiLineString
                        elif 'Point' in geom_type:
                            return 'MultiPoint'  # Promote to MultiPoint
                        else:
                            return geom_type
            
            return "Unknown"
        except Exception as e:
            return f"Error detecting geometry: {str(e)}"
    
    def _import_with_geometry_type(self, shapefile_path, conn_str, geometry_type):
        """Fallback method to import with GEOMETRY type (most flexible)"""
        try:
            # Try with GEOMETRY type (accepts any geometry type)
            cmd = [
                'ogr2ogr',
                '-f', 'PostgreSQL',
                conn_str,
                shapefile_path,
                '-nln', self.table_name,
                '-overwrite',
                '-lco', 'GEOMETRY_NAME=geom',
                '-lco', 'FID=gid',
                '-nlt', 'GEOMETRY',  # Use generic GEOMETRY type
                '-lco', 'SPATIAL_INDEX=GIST',
                '-lco', 'PRECISION=NO',
                '-t_srs', 'EPSG:4326'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.status = 'success'
                self.save()
                return True, f"Shapefile imported successfully with GEOMETRY type. Detected: {geometry_type}"
            else:
                self.status = 'error'
                self.save()
                return False, f"Error importing shapefile with GEOMETRY type: {result.stderr}"
                
        except Exception as e:
            self.status = 'error'
            self.save()
            return False, f"Exception during fallback import: {str(e)}"
    
    def get_table_info(self):
        """Get information about the created table"""
        try:
            with connections['datastore'].cursor() as cursor:
                cursor.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{self.table_name}'
                    ORDER BY ordinal_position
                """)
                columns = cursor.fetchall()
                
                cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                count = cursor.fetchone()[0]
                
                # Get geometry type information
                cursor.execute(f"""
                    SELECT ST_GeometryType(geom) as geom_type, 
                           ST_SRID(geom) as srid
                    FROM {self.table_name} 
                    WHERE geom IS NOT NULL 
                    LIMIT 1
                """)
                geom_info = cursor.fetchone()
                
                info = {
                    'columns': columns,
                    'row_count': count
                }
                
                if geom_info:
                    info['geometry_type'] = geom_info[0]
                    info['srid'] = geom_info[1]
                
                return info
        except Exception as e:
            return {'error': str(e)}

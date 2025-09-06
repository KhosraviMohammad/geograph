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
            
            # ogr2ogr command
            cmd = [
                'ogr2ogr',
                '-f', 'PostgreSQL',
                conn_str,
                shapefile_path,
                '-nln', self.table_name,
                '-overwrite',
                '-lco', 'GEOMETRY_NAME=geom',
                '-lco', 'FID=gid'
            ]
            
            # Execute ogr2ogr
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.status = 'success'
                self.save()
                return True, "Shapefile imported successfully"
            else:
                self.status = 'error'
                self.save()
                return False, f"Error importing shapefile: {result.stderr}"
                
        except Exception as e:
            self.status = 'error'
            self.save()
            return False, f"Exception during import: {str(e)}"
    
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
                
                return {
                    'columns': columns,
                    'row_count': count
                }
        except Exception as e:
            return {'error': str(e)}

from ninja import NinjaAPI, File, UploadedFile
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import zipfile
import tempfile
import shutil
from .models import ShapefileImport
from .schemas import (
    ShapefileImportSchema,
    ImportStatusResponse,
    ImportListResponse,
    SuccessResponse,
    ErrorResponse
)

# Create Ninja API instance
api = NinjaAPI(title="GeoImporter API", version="1.0.0")


@api.post("/upload/", response={200: SuccessResponse, 400: ErrorResponse, 500: ErrorResponse})
def upload_shapefile(request, shapefile: UploadedFile = File(...)):
    """Upload and import shapefile"""
    try:
        # Check if it's a zip file (shapefile)
        if not shapefile.name.endswith('.zip'):
            raise HttpError(400, "Please upload a zip file containing shapefile")
        
        # Save uploaded file
        file_path = default_storage.save(f'temp/{shapefile.name}', ContentFile(shapefile.read()))
        full_path = default_storage.path(file_path)
        
        # Extract zip file
        extract_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(full_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Find .shp file
        shp_file = None
        for file in os.listdir(extract_dir):
            if file.endswith('.shp'):
                shp_file = os.path.join(extract_dir, file)
                break
        
        if not shp_file:
            raise HttpError(400, "No .shp file found in zip")
        
        # Create ShapefileImport record
        import_record = ShapefileImport.objects.create(
            name=shapefile.name,
            file_path=shp_file,
            status='processing'
        )
        
        # Import shapefile
        success, message = import_record.import_shapefile(shp_file)
        
        # Clean up temp files
        os.remove(full_path)
        shutil.rmtree(extract_dir)
        
        if success:
            return SuccessResponse(
                message=message,
                import_id=import_record.id,
                table_name=import_record.table_name
            )
        else:
            raise HttpError(500, message)
            
    except HttpError:
        raise
    except Exception as e:
        raise HttpError(500, f"Unexpected error: {str(e)}")


@api.get("/status/{import_id}/", response={200: ImportStatusResponse, 404: ErrorResponse})
def get_import_status(request, import_id: int):
    """Get status of shapefile import"""
    try:
        import_record = get_object_or_404(ShapefileImport, id=import_id)
        
        response_data = {
            'id': import_record.id,
            'name': import_record.name,
            'status': import_record.status,
            'table_name': import_record.table_name,
            'created_at': import_record.created_at
        }
        
        if import_record.status == 'success':
            table_info = import_record.get_table_info()
            if 'error' not in table_info:
                response_data['table_info'] = table_info
        
        return response_data
        
    except Exception as e:
        raise HttpError(500, str(e))


@api.get("/list/", response={200: ImportListResponse})
def list_imports(request):
    """List all shapefile imports"""
    try:
        imports = ShapefileImport.objects.all().order_by('-created_at')
        
        imports_data = []
        for imp in imports:
            imports_data.append({
                'id': imp.id,
                'name': imp.name,
                'status': imp.status,
                'table_name': imp.table_name,
                'created_at': imp.created_at
            })
        
        return {'imports': imports_data}
        
    except Exception as e:
        raise HttpError(500, str(e))


@api.delete("/import/{import_id}/", response={200: SuccessResponse, 404: ErrorResponse})
def delete_import(request, import_id: int):
    """Delete a shapefile import record"""
    try:
        import_record = get_object_or_404(ShapefileImport, id=import_id)
        import_record.delete()
        
        return SuccessResponse(message="Import record deleted successfully")
        
    except Exception as e:
        raise HttpError(500, str(e))

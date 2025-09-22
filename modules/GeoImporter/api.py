from ninja import NinjaAPI, File, UploadedFile
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import HttpResponse
import os
import zipfile
import tempfile
import shutil
import requests
from urllib.parse import unquote
from .models import ShapefileImport
from .schemas import (
    ShapefileImportSchema,
    ImportStatusResponse,
    ImportListResponse,
    SuccessResponse,
    ErrorResponse,
    GeoServerLayerInfoSchema
)
from .geoserver_service import GeoServerService
from .geoserver_importer_service import GeoServerImporterService

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


@api.post("/upload-with-geoserver/", response={200: SuccessResponse, 400: ErrorResponse, 500: ErrorResponse})
def upload_shapefile_with_geoserver(request, shapefile: UploadedFile = File(...)):
    """Upload shapefile and automatically publish to GeoServer"""
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
        
        if not success:
            # Clean up temp files
            os.remove(full_path)
            shutil.rmtree(extract_dir)
            raise HttpError(500, message)
        
        # Publish to GeoServer
        geoserver = GeoServerService()
        
        # Create workspace if it doesn't exist
        if not geoserver.create_workspace():
            raise HttpError(500, "Failed to create GeoServer workspace")
        
        # Check if datastore exists, create if not
        datastore_name = geoserver.datastore_name
        if not geoserver.datastore_exists(datastore_name):
            if not geoserver.create_datastore(datastore_name, import_record.table_name):
                raise HttpError(500, "Failed to create GeoServer datastore")
        
        # Publish layer
        layer_name = f"layer_{import_record.table_name}"
        if not geoserver.publish_layer(datastore_name, import_record.table_name, layer_name):
            raise HttpError(500, "Failed to publish layer to GeoServer")
        
        # Get layer URLs
        wms_url = geoserver.get_wms_url(layer_name)
        wfs_url = geoserver.get_wfs_url(layer_name)
        
        # Update import record with GeoServer info
        import_record.geoserver_layer = layer_name
        import_record.geoserver_wms_url = wms_url
        import_record.geoserver_wfs_url = wfs_url
        import_record.published_to_geoserver = True
        import_record.save()
        
        # Clean up temp files
        os.remove(full_path)
        shutil.rmtree(extract_dir)
        
        return SuccessResponse(
            message=f"Shapefile imported and published to GeoServer successfully. {message}",
            import_id=import_record.id,
            table_name=import_record.table_name,
            geoserver_layer=layer_name,
            wms_url=wms_url,
            wfs_url=wfs_url
        )
            
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
            'created_at': import_record.created_at,
            'geoserver_layer': import_record.geoserver_layer,
            'geoserver_wms_url': import_record.geoserver_wms_url,
            'geoserver_wfs_url': import_record.geoserver_wfs_url,
            'published_to_geoserver': import_record.published_to_geoserver
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
                'created_at': imp.created_at,
                'geoserver_layer': imp.geoserver_layer,
                'geoserver_wms_url': imp.geoserver_wms_url,
                'geoserver_wfs_url': imp.geoserver_wfs_url,
                'published_to_geoserver': imp.published_to_geoserver
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


@api.post("/publish/{import_id}/", response={200: SuccessResponse, 400: ErrorResponse, 500: ErrorResponse})
def publish_to_geoserver(request, import_id: int):
    """Publish imported shapefile to GeoServer"""
    try:
        import_record = get_object_or_404(ShapefileImport, id=import_id)
        
        if import_record.status != 'success':
            raise HttpError(400, "Import must be successful before publishing to GeoServer")
        
        # Initialize GeoServer service
        geoserver = GeoServerService()
        
        # Create workspace if it doesn't exist
        if not geoserver.create_workspace():
            raise HttpError(500, "Failed to create GeoServer workspace")
        
        # Check if datastore exists, create if not
        datastore_name = geoserver.datastore_name
        if not geoserver.datastore_exists(datastore_name):
            if not geoserver.create_datastore(datastore_name, import_record.table_name):
                raise HttpError(500, "Failed to create GeoServer datastore")
        
        # Publish layer
        layer_name = f"layer_{import_record.table_name}"
        if not geoserver.publish_layer(datastore_name, import_record.table_name, layer_name):
            raise HttpError(500, "Failed to publish layer to GeoServer")
        
        # Get layer URLs
        wms_url = geoserver.get_wms_url(layer_name)
        wfs_url = geoserver.get_wfs_url(layer_name)
        
        # Update import record with GeoServer info
        import_record.geoserver_layer = layer_name
        import_record.geoserver_wms_url = wms_url
        import_record.geoserver_wfs_url = wfs_url
        import_record.save()
        
        return SuccessResponse(
            message="Layer published to GeoServer successfully",
            import_id=import_record.id,
            table_name=import_record.table_name,
            geoserver_layer=layer_name,
            wms_url=wms_url,
            wfs_url=wfs_url
        )
        
    except HttpError:
        raise
    except Exception as e:
        raise HttpError(500, f"Unexpected error: {str(e)}")


@api.get("/geoserver/layers/", response={200: dict, 500: ErrorResponse})
def list_geoserver_layers(request):
    """List all layers published to GeoServer"""
    try:
        geoserver = GeoServerService()
        
        # Get layers from GeoServer
        url = f"{geoserver.base_url}/rest/layers"
        response = requests.get(
            url,
            auth=geoserver._get_auth(),
            headers=geoserver._get_headers()
        )
        
        if response.status_code == 200:
            layers_data = response.json()
            return {"layers": layers_data.get('layers', {}).get('layer', [])}
        else:
            raise HttpError(500, f"Failed to get layers from GeoServer: {response.text}")
            
    except Exception as e:
        raise HttpError(500, str(e))


# GeoServer Importer Plugin Endpoints
@api.post("/geoserver-import/upload/", response={200: SuccessResponse, 400: ErrorResponse, 500: ErrorResponse})
def upload_to_geoserver_importer(request, shapefile: UploadedFile = File(...)):
    """Upload shapefile directly to GeoServer using Importer Plugin"""
    try:
        # Check if it's a zip file (shapefile)
        if not shapefile.name.endswith('.zip'):
            raise HttpError(400, "Please upload a zip file containing shapefile")
        
        # Read file data
        file_data = shapefile.read()
        
        # Initialize GeoServer Importer service
        importer = GeoServerImporterService()
        
        # Create import task in GeoServer
        import_result = importer.create_import_task(file_data, shapefile.name)
        
        if not import_result:
            raise HttpError(500, "Failed to create import task in GeoServer")
        
        import_id = import_result.get('import', {}).get('id')
        if not import_id:
            raise HttpError(500, "No import ID returned from GeoServer")
        
        return SuccessResponse(
            message="Shapefile uploaded to GeoServer Importer successfully",
            import_id=import_id,
            geoserver_import_id=import_id,
            status=import_result.get('import', {}).get('state', 'unknown')
        )
        
    except HttpError:
        raise
    except Exception as e:
        raise HttpError(500, f"Unexpected error: {str(e)}")


@api.get("/geoserver-import/status/{import_id}/", response={200: dict, 404: ErrorResponse, 500: ErrorResponse})
def get_geoserver_import_status(request, import_id: int):
    """Get status of GeoServer import task"""
    try:
        importer = GeoServerImporterService()
        
        import_status = importer.get_import_status(import_id)
        
        if not import_status:
            raise HttpError(404, "Import task not found")
        
        return import_status
        
    except HttpError:
        raise
    except Exception as e:
        raise HttpError(500, str(e))


@api.get("/geoserver-import/list/", response={200: dict, 500: ErrorResponse})
def list_geoserver_imports(request):
    """List all GeoServer import tasks"""
    try:
        importer = GeoServerImporterService()
        
        imports_data = importer.list_imports()
        
        if not imports_data:
            return {"imports": []}
        
        return imports_data
        
    except Exception as e:
        raise HttpError(500, str(e))


@api.delete("/geoserver-import/{import_id}/", response={200: SuccessResponse, 404: ErrorResponse, 500: ErrorResponse})
def delete_geoserver_import(request, import_id: int):
    """Delete a GeoServer import task"""
    try:
        importer = GeoServerImporterService()
        
        success = importer.delete_import(import_id)
        
        if not success:
            raise HttpError(404, "Import task not found or could not be deleted")
        
        return SuccessResponse(message="GeoServer import task deleted successfully")
        
    except HttpError:
        raise
    except Exception as e:
        raise HttpError(500, str(e))


@api.get("/geoserver-info/{import_id}/", response={200: GeoServerLayerInfoSchema, 404: ErrorResponse, 500: ErrorResponse})
def get_geoserver_info(request, import_id: int):
    """Get GeoServer information for a specific import"""
    try:
        import_record = get_object_or_404(ShapefileImport, id=import_id)
        
        if not import_record.published_to_geoserver or not import_record.geoserver_layer:
            raise HttpError(404, "Layer not published to GeoServer")
        
        # Get additional layer info from GeoServer
        geoserver = GeoServerService()
        layer_info = geoserver.get_layer_info(import_record.geoserver_layer)
        
        response_data = {
            'layer_name': import_record.geoserver_layer,
            'wms_url': import_record.geoserver_wms_url or geoserver.get_wms_url(import_record.geoserver_layer),
            'wfs_url': import_record.geoserver_wfs_url or geoserver.get_wfs_url(import_record.geoserver_layer),
            'capabilities_url': geoserver.get_capabilities_url('wms'),
            'workspace': geoserver.workspace,
            'datastore': geoserver.datastore_name,
            'geometry_type': layer_info.get('geometry_type') if layer_info else None,
            'srid': layer_info.get('srid') if layer_info else None,
            'feature_count': layer_info.get('feature_count') if layer_info else None
        }
        
        return response_data
        
    except HttpError:
        raise
    except Exception as e:
        raise HttpError(500, str(e))


@api.get("/geoserver-import/layer-info/{layer_name}/", response={200: GeoServerLayerInfoSchema, 404: ErrorResponse, 500: ErrorResponse})
def get_geoserver_layer_info(request, layer_name: str):
    """Get information about a layer created by GeoServer Importer"""
    try:
        importer = GeoServerImporterService()
        
        layer_info = importer.get_layer_info(layer_name)
        
        if not layer_info:
            raise HttpError(404, "Layer not found")
        
        # Prepare response data
        response_data = {
            'layer_name': layer_name,
            'wms_url': importer.get_wms_url(layer_name),
            'wfs_url': importer.get_wfs_url(layer_name),
            'capabilities_url': importer.get_capabilities_url('wms'),
            'workspace': importer.workspace,
            'datastore': None,  # Could be extracted from layer_info if available
            'geometry_type': layer_info.get('geometry_type'),
            'srid': layer_info.get('srid'),
            'feature_count': layer_info.get('feature_count')
        }
        
        return response_data
        
    except HttpError:
        raise
    except Exception as e:
        raise HttpError(500, str(e))


@api.get("/proxy/")
def proxy_geoserver(request, url: str):
    """Simple proxy for GeoServer WFS requests"""
    try:
        print(f"Proxy request received for URL: {url}")
        # Decode the URL parameter
        decoded_url = unquote(url)
        
        # Add outputFormat=application/json to WFS URL
        separator = '&' if '?' in decoded_url else '?'
        geojson_url = f"{decoded_url}{separator}outputFormat=application/json"
        
        print(f"Modified URL for GeoJSON: {geojson_url}")
        
        # Make request to GeoServer
        response = requests.get(geojson_url, timeout=30)
        
        # Return the response with proper headers
        return HttpResponse(
            response.content,
            content_type='application/json',
            status=response.status_code
        )
        
    except Exception as e:
        raise HttpError(500, f"Proxy error: {str(e)}")

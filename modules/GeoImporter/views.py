from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import zipfile
import tempfile
from .models import ShapefileImport
import json
from inertia import render as inertia_render

@csrf_exempt
@require_http_methods(["POST"])
def upload_shapefile(request):
    """Upload and import shapefile"""
    try:
        if 'shapefile' not in request.FILES:
            return JsonResponse({'error': 'No shapefile provided'}, status=400)
        
        uploaded_file = request.FILES['shapefile']
        
        # Check if it's a zip file (shapefile)
        if not uploaded_file.name.endswith('.zip'):
            return JsonResponse({'error': 'Please upload a zip file containing shapefile'}, status=400)
        
        # Save uploaded file
        file_path = default_storage.save(f'temp/{uploaded_file.name}', ContentFile(uploaded_file.read()))
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
            return JsonResponse({'error': 'No .shp file found in zip'}, status=400)
        
        # Create ShapefileImport record
        import_record = ShapefileImport.objects.create(
            name=uploaded_file.name,
            file_path=shp_file,
            status='processing'
        )
        
        # Import shapefile
        success, message = import_record.import_shapefile(shp_file)
        
        # Clean up temp files
        os.remove(full_path)
        import shutil
        shutil.rmtree(extract_dir)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'import_id': import_record.id,
                'table_name': import_record.table_name
            })
        else:
            return JsonResponse({
                'success': False,
                'error': message
            }, status=500)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)

def get_import_status(request, import_id):
    """Get status of shapefile import"""
    try:
        import_record = ShapefileImport.objects.get(id=import_id)
        
        response_data = {
            'id': import_record.id,
            'name': import_record.name,
            'status': import_record.status,
            'table_name': import_record.table_name,
            'created_at': import_record.created_at.isoformat()
        }
        
        if import_record.status == 'success':
            table_info = import_record.get_table_info()
            response_data['table_info'] = table_info
        
        return JsonResponse(response_data)
        
    except ShapefileImport.DoesNotExist:
        return JsonResponse({'error': 'Import record not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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
                'created_at': imp.created_at.isoformat()
            })
        
        return JsonResponse({'imports': imports_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def test_inertia(request):
    """Test view for Inertia.js"""
    return inertia_render(request, 'TestPage', {
        'message': 'سلام! این یک تست Inertia.js است',
        'data': {
            'name': 'Geograph',
            'version': '1.0.0'
        }
    })

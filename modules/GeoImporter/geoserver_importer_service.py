import requests
import json
import os
from django.conf import settings
from typing import Dict, Any, Optional

class GeoServerImporterService:
    """Service for using GeoServer Importer Plugin directly"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'GEOSERVER_URL', 'http://localhost:8081/geoserver')
        self.username = getattr(settings, 'GEOSERVER_USERNAME', 'admin')
        self.password = getattr(settings, 'GEOSERVER_PASSWORD', 'geoserver')
        self.workspace = getattr(settings, 'GEOSERVER_WORKSPACE', 'geograph')
        
    def _get_auth(self):
        """Get authentication tuple for requests"""
        return (self.username, self.password)
    
    def _get_headers(self):
        """Get headers for requests"""
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _get_multipart_headers(self):
        """Get headers for multipart requests"""
        return {
            'Accept': 'application/json'
        }
    
    def create_import_task(self, file_data: bytes, filename: str) -> Optional[Dict[str, Any]]:
        """Create a new import task in GeoServer"""
        url = f"{self.base_url}/rest/imports"
        
        # Prepare multipart form data
        files = {
            'file': (filename, file_data, 'application/zip')
        }
        
        data = {
            'targetWorkspace': self.workspace,
            'targetStore': 'new',  # Create new store
            'targetLayerName': filename.replace('.zip', ''),
            'createLayer': 'true'
        }
        
        try:
            response = requests.post(
                url,
                auth=self._get_auth(),
                headers=self._get_multipart_headers(),
                files=files,
                data=data
            )
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"Error creating import task: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Exception creating import task: {str(e)}")
            return None
    
    def get_import_status(self, import_id: int) -> Optional[Dict[str, Any]]:
        """Get status of an import task"""
        url = f"{self.base_url}/rest/imports/{import_id}"
        
        try:
            response = requests.get(
                url,
                auth=self._get_auth(),
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error getting import status: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Exception getting import status: {str(e)}")
            return None
    
    def list_imports(self) -> Optional[Dict[str, Any]]:
        """List all import tasks"""
        url = f"{self.base_url}/rest/imports"
        
        try:
            response = requests.get(
                url,
                auth=self._get_auth(),
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error listing imports: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Exception listing imports: {str(e)}")
            return None
    
    def delete_import(self, import_id: int) -> bool:
        """Delete an import task"""
        url = f"{self.base_url}/rest/imports/{import_id}"
        
        try:
            response = requests.delete(
                url,
                auth=self._get_auth(),
                headers=self._get_headers()
            )
            
            if response.status_code in [200, 204]:
                return True
            else:
                print(f"Error deleting import: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Exception deleting import: {str(e)}")
            return False
    
    def get_layer_info(self, layer_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a published layer"""
        url = f"{self.base_url}/rest/layers/{self.workspace}:{layer_name}"
        
        try:
            response = requests.get(
                url,
                auth=self._get_auth(),
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error getting layer info: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Exception getting layer info: {str(e)}")
            return None
    
    def get_wms_url(self, layer_name: str) -> str:
        """Get WMS URL for a layer"""
        return f"{self.base_url}/wms?service=WMS&version=1.1.0&request=GetMap&layers={self.workspace}:{layer_name}&styles=&bbox=-180,-90,180,90&width=768&height=384&srs=EPSG:4326&format=image/png"
    
    def get_wfs_url(self, layer_name: str) -> str:
        """Get WFS URL for a layer"""
        return f"{self.base_url}/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName={self.workspace}:{layer_name}&maxFeatures=50"
    
    def get_capabilities_url(self, service_type: str = 'wms') -> str:
        """Get capabilities URL for a service"""
        return f"{self.base_url}/{service_type}?service={service_type.upper()}&version=1.1.0&request=GetCapabilities"

import requests
import json
import os
from django.conf import settings
from typing import Dict, Any, Optional

class GeoServerService:
    """Service for interacting with GeoServer REST API"""
    
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
    
    def create_workspace(self, workspace_name: str = None) -> bool:
        """Create a workspace in GeoServer"""
        if not workspace_name:
            workspace_name = self.workspace
            
        url = f"{self.base_url}/rest/workspaces"
        
        data = {
            "workspace": {
                "name": workspace_name
            }
        }
        
        try:
            response = requests.post(
                url,
                auth=self._get_auth(),
                headers=self._get_headers(),
                data=json.dumps(data)
            )
            
            if response.status_code in [200, 201]:
                return True
            elif response.status_code == 409:  # Workspace already exists
                return True
            else:
                print(f"Error creating workspace: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Exception creating workspace: {str(e)}")
            return False
    
    def create_datastore(self, datastore_name: str, table_name: str) -> bool:
        """Create a PostGIS datastore in GeoServer"""
        url = f"{self.base_url}/rest/workspaces/{self.workspace}/datastores"
        
        # Get database connection details
        db_config = settings.DATABASES['datastore']
        
        data = {
            "dataStore": {
                "name": datastore_name,
                "type": "PostGIS",
                "enabled": True,
                "connectionParameters": {
                    "host": db_config['HOST'],
                    "port": db_config['PORT'],
                    "database": db_config['NAME'],
                    "user": db_config['USER'],
                    "passwd": db_config['PASSWORD'],
                    "dbtype": "postgis",
                    "schema": "public"
                }
            }
        }
        
        try:
            response = requests.post(
                url,
                auth=self._get_auth(),
                headers=self._get_headers(),
                data=json.dumps(data)
            )
            
            if response.status_code in [200, 201]:
                return True
            elif response.status_code == 409:  # Datastore already exists
                return True
            else:
                print(f"Error creating datastore: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Exception creating datastore: {str(e)}")
            return False
    
    def publish_layer(self, datastore_name: str, table_name: str, layer_name: str = None) -> bool:
        """Publish a layer from PostGIS table to GeoServer"""
        if not layer_name:
            layer_name = table_name
            
        url = f"{self.base_url}/rest/workspaces/{self.workspace}/datastores/{datastore_name}/featuretypes"
        
        data = {
            "featureType": {
                "name": layer_name,
                "nativeName": table_name,
                "title": layer_name,
                "abstract": f"Layer imported from {table_name}",
                "enabled": True,
                "srs": "EPSG:4326",
                "nativeCRS": "EPSG:4326",
                "projectionPolicy": "FORCE_DECLARED"
            }
        }
        
        try:
            response = requests.post(
                url,
                auth=self._get_auth(),
                headers=self._get_headers(),
                data=json.dumps(data)
            )
            
            if response.status_code in [200, 201]:
                return True
            elif response.status_code == 409:  # Layer already exists
                return True
            else:
                print(f"Error publishing layer: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Exception publishing layer: {str(e)}")
            return False
    
    def get_layer_info(self, layer_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a published layer"""
        url = f"{self.base_url}/rest/layers/{layer_name}"
        
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
    
    def delete_layer(self, layer_name: str) -> bool:
        """Delete a layer from GeoServer"""
        url = f"{self.base_url}/rest/layers/{layer_name}"
        
        try:
            response = requests.delete(
                url,
                auth=self._get_auth(),
                headers=self._get_headers()
            )
            
            if response.status_code in [200, 204]:
                return True
            else:
                print(f"Error deleting layer: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Exception deleting layer: {str(e)}")
            return False
    
    def get_wms_url(self, layer_name: str) -> str:
        """Get WMS URL for a layer"""
        return f"{self.base_url}/wms?service=WMS&version=1.1.0&request=GetMap&layers={self.workspace}:{layer_name}&styles=&bbox=-180,-90,180,90&width=768&height=384&srs=EPSG:4326&format=image/png"
    
    def get_wfs_url(self, layer_name: str) -> str:
        """Get WFS URL for a layer"""
        return f"{self.base_url}/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName={self.workspace}:{layer_name}&maxFeatures=50"

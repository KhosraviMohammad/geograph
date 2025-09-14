from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ShapefileImport


@admin.register(ShapefileImport)
class ShapefileImportAdmin(admin.ModelAdmin):
    """Admin interface for ShapefileImport model"""
    
    list_display = [
        'id', 'name', 'table_name', 'status', 'created_at', 
        'published_to_geoserver', 'geoserver_layer_link', 'row_count'
    ]
    
    list_filter = [
        'status', 'published_to_geoserver', 'created_at'
    ]
    
    search_fields = [
        'name', 'table_name', 'geoserver_layer'
    ]
    
    readonly_fields = [
        'id', 'created_at', 'table_name', 'file_path', 
        'geoserver_layer', 'geoserver_wms_url', 'geoserver_wfs_url',
        'table_info_display', 'wms_preview_link', 'wfs_preview_link'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'file_path', 'table_name', 'status', 'created_at')
        }),
        ('GeoServer Information', {
            'fields': (
                'published_to_geoserver', 'geoserver_layer', 
                'wms_preview_link', 'wfs_preview_link'
            ),
            'classes': ('collapse',)
        }),
        ('Table Information', {
            'fields': ('table_info_display',),
            'classes': ('collapse',)
        })
    )
    
    ordering = ['-created_at']
    
    def geoserver_layer_link(self, obj):
        """Display GeoServer layer as a clickable link"""
        if obj.geoserver_layer:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                f"http://localhost:8081/geoserver/rest/layers/{obj.geoserver_layer}",
                obj.geoserver_layer
            )
        return "Not published"
    geoserver_layer_link.short_description = "GeoServer Layer"
    geoserver_layer_link.admin_order_field = 'geoserver_layer'
    
    def wms_preview_link(self, obj):
        """Display WMS URL as a clickable link"""
        if obj.geoserver_wms_url:
            return format_html(
                '<a href="{}" target="_blank">WMS Preview</a>',
                obj.geoserver_wms_url
            )
        return "Not available"
    wms_preview_link.short_description = "WMS URL"
    
    def wfs_preview_link(self, obj):
        """Display WFS URL as a clickable link"""
        if obj.geoserver_wfs_url:
            return format_html(
                '<a href="{}" target="_blank">WFS Data</a>',
                obj.geoserver_wfs_url
            )
        return "Not available"
    wfs_preview_link.short_description = "WFS URL"
    
    def row_count(self, obj):
        """Display number of rows in the table"""
        if obj.status == 'success':
            try:
                table_info = obj.get_table_info()
                if 'error' not in table_info:
                    return table_info.get('row_count', 'Unknown')
            except:
                pass
        return "N/A"
    row_count.short_description = "Row Count"
    row_count.admin_order_field = 'status'
    
    def table_info_display(self, obj):
        """Display detailed table information"""
        if obj.status == 'success':
            try:
                table_info = obj.get_table_info()
                if 'error' not in table_info:
                    info_html = f"""
                    <div style="font-family: monospace; font-size: 12px;">
                        <strong>Row Count:</strong> {table_info.get('row_count', 'Unknown')}<br>
                        <strong>Geometry Type:</strong> {table_info.get('geometry_type', 'Unknown')}<br>
                        <strong>SRID:</strong> {table_info.get('srid', 'Unknown')}<br>
                        <strong>Columns:</strong><br>
                    """
                    
                    for column in table_info.get('columns', []):
                        info_html += f"&nbsp;&nbsp;• {column[0]} ({column[1]})<br>"
                    
                    info_html += "</div>"
                    return mark_safe(info_html)
                else:
                    return f"Error: {table_info['error']}"
            except Exception as e:
                return f"Error retrieving table info: {str(e)}"
        return "Table not available"
    table_info_display.short_description = "Table Information"
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view"""
        return super().get_queryset(request).select_related()
    
    def has_add_permission(self, request):
        """Disable adding new records through admin (use API instead)"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Allow changing status and GeoServer fields"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow deleting records"""
        return True
    
    actions = ['publish_to_geoserver', 'unpublish_from_geoserver', 'refresh_table_info']
    
    def publish_to_geoserver(self, request, queryset):
        """Action to publish selected imports to GeoServer"""
        from .geoserver_service import GeoServerService
        
        geoserver = GeoServerService()
        success_count = 0
        error_count = 0
        
        for obj in queryset:
            if obj.status == 'success' and not obj.published_to_geoserver:
                try:
                    # Create workspace if it doesn't exist
                    if not geoserver.create_workspace():
                        error_count += 1
                        continue
                    
                    # Check if datastore exists, create if not
                    datastore_name = geoserver.datastore_name
                    if not geoserver.datastore_exists(datastore_name):
                        if not geoserver.create_datastore(datastore_name, obj.table_name):
                            error_count += 1
                            continue
                    
                    # Publish layer
                    layer_name = f"layer_{obj.table_name}"
                    if geoserver.publish_layer(datastore_name, obj.table_name, layer_name):
                        # Update model
                        obj.geoserver_layer = layer_name
                        obj.geoserver_wms_url = geoserver.get_wms_url(layer_name)
                        obj.geoserver_wfs_url = geoserver.get_wfs_url(layer_name)
                        obj.published_to_geoserver = True
                        obj.save()
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
        
        if success_count > 0:
            self.message_user(request, f"Successfully published {success_count} layer(s) to GeoServer.")
        if error_count > 0:
            self.message_user(request, f"Failed to publish {error_count} layer(s) to GeoServer.", level='WARNING')
    
    publish_to_geoserver.short_description = "Publish selected imports to GeoServer"
    
    def unpublish_from_geoserver(self, request, queryset):
        """Action to unpublish selected imports from GeoServer"""
        from .geoserver_service import GeoServerService
        
        geoserver = GeoServerService()
        success_count = 0
        error_count = 0
        
        for obj in queryset:
            if obj.published_to_geoserver and obj.geoserver_layer:
                try:
                    if geoserver.delete_layer(obj.geoserver_layer):
                        # Update model
                        obj.geoserver_layer = None
                        obj.geoserver_wms_url = None
                        obj.geoserver_wfs_url = None
                        obj.published_to_geoserver = False
                        obj.save()
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
        
        if success_count > 0:
            self.message_user(request, f"Successfully unpublished {success_count} layer(s) from GeoServer.")
        if error_count > 0:
            self.message_user(request, f"Failed to unpublish {error_count} layer(s) from GeoServer.", level='WARNING')
    
    unpublish_from_geoserver.short_description = "Unpublish selected imports from GeoServer"
    
    def refresh_table_info(self, request, queryset):
        """Action to refresh table information for selected imports"""
        success_count = 0
        error_count = 0
        
        for obj in queryset:
            if obj.status == 'success':
                try:
                    # Just trigger the get_table_info method to refresh
                    table_info = obj.get_table_info()
                    if 'error' not in table_info:
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
        
        if success_count > 0:
            self.message_user(request, f"Successfully refreshed table info for {success_count} import(s).")
        if error_count > 0:
            self.message_user(request, f"Failed to refresh table info for {error_count} import(s).", level='WARNING')
    
    refresh_table_info.short_description = "Refresh table information"

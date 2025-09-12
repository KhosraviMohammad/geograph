from ninja import Schema
from typing import Optional, List, Dict, Any
from datetime import datetime


class ShapefileImportSchema(Schema):
    id: int
    name: str
    table_name: str
    status: str
    created_at: datetime
    geoserver_layer: Optional[str] = None
    geoserver_wms_url: Optional[str] = None
    geoserver_wfs_url: Optional[str] = None
    published_to_geoserver: bool = False


class ShapefileImportCreateSchema(Schema):
    name: str


class TableInfoSchema(Schema):
    columns: List[List[str]]
    row_count: int
    geometry_type: Optional[str] = None
    srid: Optional[int] = None


class ImportStatusResponse(Schema):
    id: int
    name: str
    status: str
    table_name: str
    created_at: datetime
    table_info: Optional[TableInfoSchema] = None


class ImportListResponse(Schema):
    imports: List[ShapefileImportSchema]


class SuccessResponse(Schema):
    success: bool = True
    message: str
    import_id: Optional[int] = None
    table_name: Optional[str] = None


class ErrorResponse(Schema):
    success: bool = False
    error: str

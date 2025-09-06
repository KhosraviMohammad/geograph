from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_shapefile, name='upload_shapefile'),
    path('status/<int:import_id>/', views.get_import_status, name='get_import_status'),
    path('list/', views.list_imports, name='list_imports'),
]

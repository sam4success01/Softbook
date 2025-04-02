from django.urls import path
from . import views

app_name = 'fixed_assets'

urlpatterns = [
    path('', views.home, name='home'),
    path('assets/', views.asset_list, name='asset_list'),
    path('assets/add/', views.asset_create, name='asset_create'),
    path('assets/<int:pk>/', views.asset_detail, name='asset_detail'),
    path('assets/<int:pk>/edit/', views.asset_edit, name='asset_edit'),
    path('assets/<int:pk>/delete/', views.asset_delete, name='asset_delete'),
    path('categories/', views.category_list, name='category_list'),
    path('depreciation/', views.depreciation_report, name='depreciation_report'),
    path('maintenance/', views.maintenance_list, name='maintenance_list'),
]
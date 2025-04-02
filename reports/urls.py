from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.home, name='home'),
    path('financial/', views.financial_reports, name='financial_reports'),
    path('balance-sheet/', views.balance_sheet, name='balance_sheet'),
    path('income-statement/', views.income_statement, name='income_statement'),
    path('cash-flow/', views.cash_flow, name='cash_flow'),
    path('tax/', views.tax_reports, name='tax_reports'),
    path('custom/', views.custom_reports, name='custom_reports'),
    path('custom/create/', views.create_custom_report, name='create_custom_report'),
    path('custom/<int:pk>/', views.custom_report_detail, name='custom_report_detail'),
    path('custom/<int:pk>/edit/', views.edit_custom_report, name='edit_custom_report'),
    path('schedules/', views.report_schedules, name='report_schedules'),
    path('schedules/create/', views.create_schedule, name='create_schedule'),
    path('schedules/<int:pk>/edit/', views.edit_schedule, name='edit_schedule'),
    path('export/<str:report_type>/', views.export_report, name='export_report'),
    path('settings/', views.report_settings, name='settings'),
]
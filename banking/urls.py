from django.urls import path
from . import views

app_name = 'banking'

urlpatterns = [
    path('', views.home, name='home'),
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/add/', views.account_create, name='account_create'),
    path('accounts/<int:pk>/', views.account_detail, name='account_detail'),
    path('accounts/<int:pk>/edit/', views.account_edit, name='account_edit'),
    path('transactions/', views.transaction_list, name='transactions'),
    path('transactions/add/', views.transaction_create, name='transaction_create'),
    path('transactions/<int:pk>/', views.transaction_detail, name='transaction_detail'),
    path('transactions/<int:pk>/edit/', views.transaction_edit, name='transaction_edit'),
    path('reconciliation/', views.reconciliation, name='reconciliation'),
    path('reconciliation/start/', views.start_reconciliation, name='start_reconciliation'),
    path('statements/', views.statement_list, name='statement_list'),
    path('statements/upload/', views.statement_upload, name='statement_upload'),
    path('statements/<int:pk>/', views.statement_detail, name='statement_detail'),
    path('connections/', views.bank_connections, name='connections'),
    path('connections/add/', views.add_connection, name='add_connection'),
]
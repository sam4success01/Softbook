from django.urls import path
from . import views

app_name = 'invoicing'

urlpatterns = [
    # Dashboard
    path('', views.home, name='home'),
    
    # Invoices
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('invoices/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    path('invoices/<int:pk>/send/', views.invoice_send, name='invoice_send'),
    path('invoices/<int:pk>/print/', views.invoice_print, name='invoice_print'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('invoices/<uuid:public_url>/', views.invoice_public, name='invoice_public'),
    path('invoices/<int:pk>/record-payment/', views.record_payment, name='record_payment'),
    
    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    
    # Items
    path('items/', views.item_list, name='item_list'),
    path('items/create/', views.item_create, name='item_create'),
    path('items/<int:pk>/edit/', views.item_edit, name='item_edit'),
    path('items/<int:pk>/delete/', views.item_delete, name='item_delete'),
    
    # Templates
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:pk>/edit/', views.template_edit, name='template_edit'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    path('templates/<int:pk>/set-default/', views.template_set_default, name='template_set_default'),
    
    # Payments
    path('payments/', views.payment_list, name='payment_list'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/aging/', views.aging_report, name='aging_report'),
    path('reports/revenue/', views.revenue_report, name='revenue_report'),
    path('reports/customer-analysis/', views.customer_analysis, name='customer_analysis'),
    path('reports/product-performance/', views.product_performance, name='product_performance'),
    path('reports/cash-flow/', views.cash_flow, name='cash_flow'),
    
    # Settings
    path('settings/', views.settings_view, name='settings'),
]
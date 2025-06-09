# payables/urls.py

from django.urls import path
from . import views

app_name = 'payables'

urlpatterns = [
    # Dashboard
    path('', views.home, name='home'),
    
    # Vendors
    path('vendors/', views.vendor_list, name='vendor_list'),
    path('vendors/create/', views.vendor_create, name='vendor_create'),
    path('vendors/<int:pk>/', views.vendor_detail, name='vendor_detail'),
    path('vendors/<int:pk>/edit/', views.vendor_edit, name='vendor_edit'),
    path('vendors/<int:pk>/delete/', views.vendor_delete, name='vendor_delete'),
    
    # Bills
    path('bills/', views.bill_list, name='bill_list'),
    path('bills/create/', views.bill_create, name='bill_create'),
    path('bills/<int:pk>/', views.bill_detail, name='bill_detail'),
    path('bills/<int:pk>/edit/', views.bill_edit, name='bill_edit'),
    path('bills/<int:pk>/delete/', views.bill_delete, name='bill_delete'),
    path('bills/<int:pk>/payment/', views.record_payment, name='bill_payment'),
    path('bills/<int:pk>/convert-to-expense/', views.convert_to_expense, name='convert_to_expense'),
    
    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/', views.expense_detail, name='expense_detail'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('expenses/<int:pk>/approve/', views.expense_approve, name='expense_approve'),
    path('expenses/<int:pk>/reject/', views.expense_reject, name='expense_reject'),
    
    # Payments
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/create/', views.payment_create, name='payment_create'),
    path('payments/<int:pk>/', views.payment_detail, name='payment_detail'),
    path('payments/<int:pk>/edit/', views.payment_edit, name='payment_edit'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
    
    # Purchase Orders
    path('purchase-orders/', views.po_list, name='po_list'),
    path('purchase-orders/create/', views.po_create, name='po_create'),
    path('purchase-orders/<int:pk>/', views.po_detail, name='po_detail'),
    path('purchase-orders/<int:pk>/edit/', views.po_edit, name='po_edit'),
    path('purchase-orders/<int:pk>/delete/', views.po_delete, name='po_delete'),
    path('purchase-orders/<int:pk>/convert-to-bill/', views.po_convert_to_bill, name='po_convert_to_bill'),
    path('purchase-orders/<int:pk>/send/', views.po_send, name='po_send'),
    
    # Expense Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # Recurring Bills
    path('recurring/', views.recurring_list, name='recurring_list'),
    path('recurring/create/', views.recurring_create, name='recurring_create'),
    path('recurring/<int:pk>/', views.recurring_detail, name='recurring_detail'),
    path('recurring/<int:pk>/edit/', views.recurring_edit, name='recurring_edit'),
    path('recurring/<int:pk>/delete/', views.recurring_delete, name='recurring_delete'),
    path('recurring/<int:pk>/create-bill/', views.recurring_create_bill, name='recurring_create_bill'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/payables-summary/', views.payables_summary, name='payables_summary'),
    path('reports/vendor-balance/', views.vendor_balance, name='vendor_balance'),
    path('reports/expense-analysis/', views.expense_analysis, name='expense_analysis'),
    path('reports/bill-payment-history/', views.bill_payment_history, name='bill_payment_history'),
    path('reports/aging-summary/', views.aging_summary, name='aging_summary'),
    
    # AJAX endpoints
    path('ajax/vendor-bills/<int:vendor_id>/', views.ajax_vendor_bills, name='ajax_vendor_bills'),
    path('ajax/bill-details/<int:bill_id>/', views.ajax_bill_details, name='ajax_bill_details'),
]
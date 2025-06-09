# payables/admin.py

from django.contrib import admin
from .models import (
    Vendor, ExpenseCategory, Bill, BillItem, Expense, Payment,
    PaymentAllocation, PurchaseOrder, PurchaseOrderItem, RecurringBill
)


class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 1
    fields = ['expense_category', 'description', 'quantity', 'unit_price', 'tax_rate', 'line_total', 'tax_amount']
    readonly_fields = ['line_total', 'tax_amount']


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 1
    fields = ['bill', 'amount']


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    fields = ['item_name', 'description', 'quantity', 'unit_price', 'tax_rate', 'line_total', 'tax_amount']
    readonly_fields = ['line_total', 'tax_amount']


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'contact_person', 'email', 'phone', 'payment_terms', 'is_active', 'created_at']
    list_filter = ['vendor_type', 'payment_terms', 'is_active', 'created_at']
    search_fields = ['company_name', 'contact_person', 'email', 'tax_number']
    fieldsets = (
        ('Basic Information', {
            'fields': ('vendor_type', 'company_name', 'contact_person', 'email', 'phone', 'website')
        }),
        ('Address', {
            'fields': ('billing_address_line1', 'billing_address_line2', 'billing_city', 
                      'billing_state', 'billing_postal_code', 'billing_country')
        }),
        ('Financial Details', {
            'fields': ('tax_number', 'payment_terms', 'custom_payment_terms', 'credit_limit', 'opening_balance')
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'bank_account_number', 'bank_routing_number', 'bank_swift_code'),
            'classes': ('collapse',)
        }),
        ('Other', {
            'fields': ('notes', 'is_active', 'created_by')
        })
    )
    readonly_fields = ['created_by']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'parent', 'is_active']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'code']
    ordering = ['code']


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['bill_number', 'vendor', 'vendor_bill_number', 'bill_date', 'due_date', 
                   'total', 'balance_due', 'status', 'created_at']
    list_filter = ['status', 'bill_date', 'due_date', 'created_at']
    search_fields = ['bill_number', 'vendor__company_name', 'vendor_bill_number']
    date_hierarchy = 'bill_date'
    inlines = [BillItemInline]
    readonly_fields = ['bill_number', 'subtotal', 'tax_amount', 'total', 'amount_paid', 'balance_due', 'created_by']
    fieldsets = (
        ('Bill Information', {
            'fields': ('bill_number', 'vendor', 'vendor_bill_number', 'bill_date', 'due_date', 'status')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total', 'amount_paid', 'balance_due')
        }),
        ('Additional Information', {
            'fields': ('notes', 'attachment', 'created_by')
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['expense_number', 'vendor', 'category', 'expense_date', 'total_amount', 
                   'payment_mode', 'status', 'is_billable', 'created_at']
    list_filter = ['status', 'payment_mode', 'is_billable', 'expense_date', 'category']
    search_fields = ['expense_number', 'vendor__company_name', 'description']
    date_hierarchy = 'expense_date'
    readonly_fields = ['expense_number', 'total_amount', 'created_by']
    fieldsets = (
        ('Expense Information', {
            'fields': ('expense_number', 'vendor', 'expense_date', 'category', 'description')
        }),
        ('Amounts', {
            'fields': ('amount', 'tax_amount', 'total_amount')
        }),
        ('Payment Details', {
            'fields': ('payment_mode', 'reference_number')
        }),
        ('Billing', {
            'fields': ('is_billable', 'customer', 'status')
        }),
        ('Additional Information', {
            'fields': ('receipt', 'notes', 'created_by')
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_number', 'vendor', 'payment_date', 'amount', 'payment_method', 
                   'reference_number', 'created_at']
    list_filter = ['payment_method', 'payment_date', 'created_at']
    search_fields = ['payment_number', 'vendor__company_name', 'reference_number']
    date_hierarchy = 'payment_date'
    inlines = [PaymentAllocationInline]
    readonly_fields = ['payment_number', 'created_by']
    fieldsets = (
        ('Payment Information', {
            'fields': ('payment_number', 'vendor', 'payment_date', 'amount')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'reference_number', 'bank_charges')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by')
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'vendor', 'po_date', 'expected_delivery_date', 
                   'total', 'status', 'created_at']
    list_filter = ['status', 'po_date', 'expected_delivery_date', 'created_at']
    search_fields = ['po_number', 'vendor__company_name']
    date_hierarchy = 'po_date'
    inlines = [PurchaseOrderItemInline]
    readonly_fields = ['po_number', 'subtotal', 'tax_amount', 'total', 'created_by']
    fieldsets = (
        ('PO Information', {
            'fields': ('po_number', 'vendor', 'po_date', 'expected_delivery_date', 'status')
        }),
        ('Delivery', {
            'fields': ('ship_to_address',)
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total')
        }),
        ('Additional Information', {
            'fields': ('terms_and_conditions', 'notes', 'created_by')
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(RecurringBill)
class RecurringBillAdmin(admin.ModelAdmin):
    list_display = ['name', 'vendor', 'frequency', 'amount', 'next_bill_date', 'is_active', 'created_at']
    list_filter = ['frequency', 'is_active', 'next_bill_date']
    search_fields = ['name', 'vendor__company_name']
    readonly_fields = ['created_by']
    fieldsets = (
        ('Recurring Bill Information', {
            'fields': ('name', 'vendor', 'frequency', 'start_date', 'end_date', 'next_bill_date')
        }),
        ('Bill Template', {
            'fields': ('category', 'amount', 'tax_rate', 'description')
        }),
        ('Status', {
            'fields': ('is_active', 'created_by')
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
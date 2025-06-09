from django.contrib import admin
from .models import Customer, Item, InvoiceTemplate, Invoice, InvoiceItem, Payment, Settings


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('get_display_name', 'email', 'phone', 'city', 'created_at')
    list_filter = ('customer_type', 'created_at')
    search_fields = ('company_name', 'first_name', 'last_name', 'email')
    date_hierarchy = 'created_at'
    
    def get_display_name(self, obj):
        if obj.customer_type == 'business' and obj.company_name:
            return f"{obj.company_name} ({obj.first_name} {obj.last_name})"
        return f"{obj.first_name} {obj.last_name}"
    get_display_name.short_description = 'Name'


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'item_type', 'unit_price', 'tax_rate', 'is_active')
    list_filter = ('item_type', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'sku')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'item_type', 'is_active')
        }),
        ('Pricing', {
            'fields': ('unit_price', 'tax_rate')
        }),
        ('Inventory', {
            'fields': ('sku',)
        }),
    )


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ('item', 'description', 'quantity', 'unit_price', 'tax_rate', 'line_total', 'tax_amount')
    readonly_fields = ('line_total', 'tax_amount')
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Make fields editable when creating a new invoice
        if obj is None:
            self.readonly_fields = ()
        return formset


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ('payment_date', 'amount', 'payment_method', 'reference_number', 'notes')
    readonly_fields = ('created_at',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'issue_date', 'due_date', 'total', 'status')
    list_filter = ('status', 'issue_date', 'due_date')
    search_fields = ('invoice_number', 'customer__company_name', 'customer__first_name', 'customer__last_name')
    date_hierarchy = 'issue_date'
    inlines = [InvoiceItemInline, PaymentInline]
    readonly_fields = ('subtotal', 'tax_amount', 'total', 'amount_paid', 'balance_due', 'created_at', 'updated_at', 'created_by')
    fieldsets = (
        (None, {
            'fields': ('invoice_number', 'customer', 'template')
        }),
        ('Dates', {
            'fields': ('issue_date', 'due_date')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total', 'amount_paid', 'balance_due')
        }),
        ('Additional Information', {
            'fields': ('notes', 'terms')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('customer', 'template')


@admin.register(InvoiceTemplate)
class InvoiceTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_default', 'created_at')
    list_filter = ('is_default', 'created_at')
    search_fields = ('name',)
    fieldsets = (
        (None, {
            'fields': ('name', 'is_default', 'logo')
        }),
        ('Content', {
            'fields': ('header', 'footer', 'terms', 'notes')
        }),
        ('Styling', {
            'fields': ('primary_color',)
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'payment_date', 'payment_method', 'reference_number')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('invoice__invoice_number', 'reference_number')
    date_hierarchy = 'payment_date'
    raw_id_fields = ('invoice',)
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'company_email', 'currency')
    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'company_address', 'company_phone', 
                       'company_email', 'company_website', 'company_tax_number', 'logo')
        }),
        ('Invoice Defaults', {
            'fields': ('default_payment_terms', 'default_tax_rate', 'invoice_prefix', 
                       'next_invoice_number', 'default_template', 'currency')
        }),
        ('Default Content', {
            'fields': ('invoice_note_default', 'invoice_terms_default')
        }),
    )
    
    def has_add_permission(self, request):
        # Allow adding settings only if none exist
        return not Settings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of settings
        return False
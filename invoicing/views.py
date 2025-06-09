from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import date, datetime
from django.urls import reverse
from datetime import datetime, timedelta
import json

from .models import Customer, Item, Invoice, InvoiceItem, InvoiceTemplate, Payment, Settings
from .forms import (
    CustomerForm, ItemForm, InvoiceForm, InvoiceItemFormSet, 
    InvoiceTemplateForm, PaymentForm, SettingsForm, InvoiceFilterForm
)


@login_required
def home(request):
    """Invoicing module home page."""
    # Get stats for dashboard
    total_invoices = Invoice.objects.count()
    total_customers = Customer.objects.count()
    
    # Calculate total amount and pending amount
    invoices = Invoice.objects.all()
    total_amount = invoices.aggregate(total=Sum('total'))['total'] or 0
    pending_amount = invoices.exclude(status='paid').aggregate(total=Sum('balance_due'))['total'] or 0
    
    # Recent invoices
    recent_invoices = invoices.order_by('-created_at')[:5]
    
    # Overdue invoices
    today = timezone.now().date()
    overdue_invoices = invoices.filter(due_date__lt=today).exclude(status__in=['paid', 'cancelled'])
    
    # Upcoming payments (invoices due in the next 7 days)
    next_week = today + timedelta(days=7)
    upcoming_payments = invoices.filter(
        due_date__gte=today, 
        due_date__lte=next_week
    ).exclude(status__in=['paid', 'cancelled'])
    
    # Calculate monthly revenue
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_revenue = invoices.filter(
        issue_date__month=current_month,
        issue_date__year=current_year,
        status='paid'
    ).aggregate(total=Sum('total'))['total'] or 0
    
    context = {
        'title': 'Invoicing Dashboard',
        'total_invoices': total_invoices,
        'total_customers': total_customers,
        'total_amount': total_amount,
        'pending_amount': pending_amount,
        'recent_invoices': recent_invoices,
        'overdue_invoices': overdue_invoices,
        'upcoming_payments': upcoming_payments,
        'monthly_revenue': monthly_revenue,
    }
    return render(request, 'invoicing/home.html', context)


@login_required
def invoice_list(request):
    """List all invoices with filtering options."""
    # Get filter form
    filter_form = InvoiceFilterForm(request.GET)
    
    # Base queryset
    invoices = Invoice.objects.all().select_related('customer')
    
    # Apply filters if the form is valid
    if filter_form.is_valid():
        filters = filter_form.cleaned_data
        
        if filters.get('status'):
            invoices = invoices.filter(status=filters['status'])
            
        if filters.get('customer'):
            invoices = invoices.filter(customer=filters['customer'])
            
        if filters.get('date_from'):
            invoices = invoices.filter(issue_date__gte=filters['date_from'])
            
        if filters.get('date_to'):
            invoices = invoices.filter(issue_date__lte=filters['date_to'])
            
        if filters.get('min_amount'):
            invoices = invoices.filter(total__gte=filters['min_amount'])
            
        if filters.get('max_amount'):
            invoices = invoices.filter(total__lte=filters['max_amount'])
    
    # Order by
    order_by = request.GET.get('order_by', '-issue_date')
    invoices = invoices.order_by(order_by)
    
    # Pagination
    paginator = Paginator(invoices, 20)  # Show 20 invoices per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate totals for displayed invoices
    total_amount = invoices.aggregate(total=Sum('total'))['total'] or 0
    paid_amount = invoices.aggregate(total=Sum('amount_paid'))['total'] or 0
    pending_amount = total_amount - paid_amount
    
    context = {
        'title': 'Invoices',
        'invoices': page_obj,
        'filter_form': filter_form,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }
    return render(request, 'invoicing/invoice_list.html', context)


@login_required
def invoice_create(request):
    """Create a new invoice."""
    # Try to get default settings
    try:
        settings = Settings.objects.first()
        default_template = settings.default_template if settings else None
    except:
        settings = None
        default_template = None
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        formset = InvoiceItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            # Save invoice but don't commit to db yet
            invoice = form.save(commit=False)
            invoice.created_by = request.user
            
            # If no template selected, use default
            if not invoice.template and default_template:
                invoice.template = default_template
            
            # Save the invoice WITHOUT triggering the save method's calculations
            # since there are no items yet
            invoice.subtotal = 0
            invoice.tax_amount = 0
            invoice.total = invoice.discount_amount or 0
            invoice.balance_due = invoice.total
            invoice.save()
            
            # Now save the formset items
            items = formset.save(commit=False)
            for item in items:
                item.invoice = invoice
                # Don't save yet - we'll save all at once
            
            # Save all items - this will trigger the invoice totals recalculation
            for item in items:
                item.save()  # This triggers the invoice.save() in InvoiceItem.save()
            
            # Handle deletions
            for item in formset.deleted_objects:
                item.delete()
            
            messages.success(request, f'Invoice #{invoice.invoice_number} created successfully.')
            
            # Determine where to redirect
            if 'save_and_send' in request.POST:
                return redirect('invoicing:invoice_send', pk=invoice.pk)
            elif 'save_and_new' in request.POST:
                return redirect('invoicing:invoice_create')
            else:
                return redirect('invoicing:invoice_detail', pk=invoice.pk)
    else:
        # Initialize with defaults from settings
        initial = {}
        if settings:
            # Set default due date based on settings
            initial['issue_date'] = timezone.now().date()
            initial['due_date'] = timezone.now().date() + timedelta(days=settings.default_payment_terms)
            initial['template'] = default_template
            
        form = InvoiceForm(initial=initial)
        formset = InvoiceItemFormSet()
    
    # Prepare items data for JavaScript
    items_json = []
    for item in Item.objects.filter(is_active=True):
        items_json.append({
            'id': item.id,
            'name': item.name,
            'description': item.description or '',
            'unit_price': float(item.unit_price),
            'tax_rate': float(item.tax_rate)
        })
    
    context = {
        'title': 'Create Invoice',
        'form': form,
        'formset': formset,
        'customers': Customer.objects.all(),
        'items': json.dumps(items_json),  # Convert to JSON string
        'templates': InvoiceTemplate.objects.all(),
    }
    return render(request, 'invoicing/invoice_form.html', context)


@login_required
def invoice_detail(request, pk):
    """Display invoice details."""
    invoice = get_object_or_404(Invoice, pk=pk)
    items = invoice.items.all()
    payments = invoice.payments.all()
    
    context = {
        'title': f'Invoice #{invoice.invoice_number}',
        'invoice': invoice,
        'items': items,
        'payments': payments,
    }
    return render(request, 'invoicing/invoice_detail.html', context)


@login_required
def invoice_edit(request, pk):
    """Edit an invoice."""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Don't allow editing of paid or cancelled invoices
    if invoice.status in ['paid', 'cancelled']:
        messages.error(request, f'Cannot edit invoice in {invoice.status} status.')
        return redirect('invoicing:invoice_detail', pk=pk)
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        formset = InvoiceItemFormSet(request.POST, instance=invoice)
        
        if form.is_valid() and formset.is_valid():
            # Save the invoice form
            invoice = form.save()
            
            # Save the formset items
            items = formset.save(commit=False)
            
            # Set invoice on new items
            for item in items:
                item.invoice = invoice
            
            # Save all items - this will trigger recalculation
            for item in items:
                item.save()
            
            # Handle deletions
            for item in formset.deleted_objects:
                item.delete()
            
            # Force a final save to ensure totals are correct
            invoice.save()
            
            messages.success(request, f'Invoice #{invoice.invoice_number} updated successfully.')
            return redirect('invoicing:invoice_detail', pk=invoice.pk)
    else:
        form = InvoiceForm(instance=invoice)
        formset = InvoiceItemFormSet(instance=invoice)
    
    # Prepare items data for JavaScript
    items_json = []
    for item in Item.objects.filter(is_active=True):
        items_json.append({
            'id': item.id,
            'name': item.name,
            'description': item.description or '',
            'unit_price': float(item.unit_price),
            'tax_rate': float(item.tax_rate)
        })
    
    context = {
        'title': f'Edit Invoice #{invoice.invoice_number}',
        'form': form,
        'formset': formset,
        'invoice': invoice,
        'customers': Customer.objects.all(),
        'items': json.dumps(items_json),  # Convert to JSON string
        'templates': InvoiceTemplate.objects.all(),
        'is_edit': True,
    }
    return render(request, 'invoicing/invoice_form.html', context)


@login_required
def invoice_delete(request, pk):
    """Delete an invoice."""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Don't allow deletion of paid invoices
    if invoice.status in ['paid', 'partially_paid']:
        messages.error(request, f'Cannot delete invoice with payments. Mark as cancelled instead.')
        return redirect('invoicing:invoice_detail', pk=pk)
    
    if request.method == 'POST':
        invoice_number = invoice.invoice_number
        invoice.delete()
        messages.success(request, f'Invoice #{invoice_number} deleted successfully.')
        return redirect('invoicing:invoice_list')
    
    context = {
        'title': f'Delete Invoice #{invoice.invoice_number}',
        'invoice': invoice,
    }
    return render(request, 'invoicing/invoice_confirm_delete.html', context)


@login_required
def invoice_send(request, pk):
    """Send invoice to customer."""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if request.method == 'POST':
        # In a real system, you would send an email here
        # For now, just mark the invoice as sent
        
        # Update status if currently draft
        if invoice.status == 'draft':
            invoice.status = 'sent'
            invoice.save()
            
        messages.success(request, f'Invoice #{invoice.invoice_number} sent to {invoice.customer.email}.')
        return redirect('invoicing:invoice_detail', pk=pk)
    
    context = {
        'title': f'Send Invoice #{invoice.invoice_number}',
        'invoice': invoice,
    }
    return render(request, 'invoicing/invoice_send.html', context)


@login_required
def invoice_print(request, pk):
    """Display printable version of invoice."""
    invoice = get_object_or_404(Invoice, pk=pk)
    items = invoice.items.all()
    
    context = {
        'invoice': invoice,
        'items': items,
    }
    return render(request, 'invoicing/invoice_print.html', context)


@login_required
def invoice_pdf(request, pk):
    """Generate PDF version of invoice."""
    # In a real implementation, you would use a library like
    # reportlab, weasyprint or xhtml2pdf to generate a PDF
    
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # For now, just redirect to the detail page
    messages.info(request, "PDF generation would happen here in a real implementation.")
    return redirect('invoicing:invoice_detail', pk=pk)


def invoice_public(request, public_url):
    """Public view of invoice for customers."""
    invoice = get_object_or_404(Invoice, public_url=public_url)
    items = invoice.items.all()
    
    # Mark as viewed if in sent status
    if invoice.status == 'sent':
        invoice.status = 'viewed'
        invoice.save()
    
    context = {
        'invoice': invoice,
        'items': items,
        'is_public': True,
    }
    return render(request, 'invoicing/invoice_public.html', context)


@login_required
def record_payment(request, pk):
    """Record a payment for an invoice."""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Don't allow payments for cancelled invoices
    if invoice.status == 'cancelled':
        messages.error(request, 'Cannot record payment for cancelled invoice.')
        return redirect('invoicing:invoice_detail', pk=pk)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.created_by = request.user
            payment.save()
            
            messages.success(request, f'Payment of ${payment.amount} recorded successfully.')
            return redirect('invoicing:invoice_detail', pk=pk)
    else:
        # Default to the remaining balance
        initial = {
            'amount': invoice.balance_due,
            'payment_date': timezone.now().date(),
        }
        form = PaymentForm(initial=initial)
    
    context = {
        'title': f'Record Payment for Invoice #{invoice.invoice_number}',
        'form': form,
        'invoice': invoice,
    }
    return render(request, 'invoicing/payment_form.html', context)


@login_required
def customer_list(request):
    """List all customers."""
    customers = Customer.objects.all()
    
    # Search functionality
    search_query = request.GET.get('q')
    if search_query:
        customers = customers.filter(
            Q(company_name__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Add invoice stats to each customer
    for customer in customers:
        customer.total_invoices = Invoice.objects.filter(customer=customer).count()
        customer.open_invoices = Invoice.objects.filter(
            customer=customer, 
            status__in=['draft', 'sent', 'viewed', 'partially_paid', 'overdue']
        ).count()
        customer.total_spent = Invoice.objects.filter(
            customer=customer, 
            status='paid'
        ).aggregate(total=Sum('total'))['total'] or 0
    
    # Pagination
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': 'Customers',
        'customers': page_obj,
        'search_query': search_query,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }
    return render(request, 'invoicing/customer_list.html', context)


@login_required
def customer_create(request):
    """Create a new customer."""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.save()
            
            messages.success(request, f'Customer {customer} created successfully.')
            
            # Redirect to appropriate page based on button clicked
            if 'save_and_new' in request.POST:
                return redirect('invoicing:customer_create')
            elif 'save_and_invoice' in request.POST:
                return redirect('invoicing:invoice_create')
            else:
                return redirect('invoicing:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm()
    
    context = {
        'title': 'Add Customer',
        'form': form,
    }
    return render(request, 'invoicing/customer_form.html', context)


@login_required
def customer_detail(request, pk):
    """Display customer details."""
    customer = get_object_or_404(Customer, pk=pk)
    
    # Get customer's invoices
    invoices = Invoice.objects.filter(customer=customer).order_by('-issue_date')
    
    # Calculate customer stats
    stats = {
        'total_invoices': invoices.count(),
        'paid_invoices': invoices.filter(status='paid').count(),
        'open_invoices': invoices.exclude(status__in=['paid', 'cancelled']).count(),
        'total_amount': invoices.aggregate(total=Sum('total'))['total'] or 0,
        'paid_amount': invoices.aggregate(total=Sum('amount_paid'))['total'] or 0,
    }
    stats['balance_due'] = stats['total_amount'] - stats['paid_amount']
    
    context = {
        'title': f'Customer: {customer}',
        'customer': customer,
        'invoices': invoices,
        'stats': stats,
    }
    return render(request, 'invoicing/customer_detail.html', context)


@login_required
def customer_edit(request, pk):
    """Edit customer information."""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        
        if form.is_valid():
            form.save()
            messages.success(request, f'Customer {customer} updated successfully.')
            return redirect('invoicing:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    
    context = {
        'title': f'Edit Customer: {customer}',
        'form': form,
        'customer': customer,
    }
    return render(request, 'invoicing/customer_form.html', context)


@login_required
def customer_delete(request, pk):
    """Delete a customer."""
    customer = get_object_or_404(Customer, pk=pk)
    
    # Check if customer has invoices
    if Invoice.objects.filter(customer=customer).exists():
        messages.error(request, f'Cannot delete customer with invoices.')
        return redirect('invoicing:customer_detail', pk=pk)
    
    if request.method == 'POST':
        customer_name = str(customer)
        customer.delete()
        messages.success(request, f'Customer {customer_name} deleted successfully.')
        return redirect('invoicing:customer_list')
    
    context = {
        'title': f'Delete Customer: {customer}',
        'customer': customer,
    }
    return render(request, 'invoicing/customer_confirm_delete.html', context)


@login_required
def item_list(request):
    """List all items/services."""
    items = Item.objects.all()
    
    # Search functionality
    search_query = request.GET.get('q')
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
    
    # Filter by type
    item_type = request.GET.get('type')
    if item_type:
        items = items.filter(item_type=item_type)
    
    # Filter by active status
    is_active = request.GET.get('is_active')
    if is_active in ['true', 'false']:
        items = items.filter(is_active=is_active == 'true')
    
    context = {
        'title': 'Products & Services',
        'item_list': items,  # <-- Changed from 'items' to 'item_list'
        'search_query': search_query,
        'item_type': item_type,
        'is_active': is_active,
    }
    return render(request, 'invoicing/item_list.html', context)


@login_required
def item_create(request):
    """Create a new item."""
    if request.method == 'POST':
        form = ItemForm(request.POST)
        
        if form.is_valid():
            item = form.save(commit=False)
            item.created_by = request.user
            item.save()
            
            messages.success(request, f'Item {item.name} created successfully.')
            
            if 'save_and_new' in request.POST:
                return redirect('invoicing:item_create')
            else:
                return redirect('invoicing:item_list')
    else:
        # Try to get default tax rate from settings
        try:
            settings = Settings.objects.first()
            initial = {'tax_rate': settings.default_tax_rate} if settings else {}
        except:
            initial = {}
            
        form = ItemForm(initial=initial)
    
    context = {
        'title': 'Add Product/Service',
        'form': form,
    }
    return render(request, 'invoicing/item_form.html', context)


@login_required
def item_edit(request, pk):
    """Edit an item."""
    item = get_object_or_404(Item, pk=pk)
    
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        
        if form.is_valid():
            form.save()
            messages.success(request, f'Item {item.name} updated successfully.')
            return redirect('invoicing:item_list')
    else:
        form = ItemForm(instance=item)
    
    context = {
        'title': f'Edit {item.get_item_type_display()}: {item.name}',
        'form': form,
        'item': item,
    }
    return render(request, 'invoicing/item_form.html', context)


@login_required
def item_delete(request, pk):
    """Delete an item."""
    item = get_object_or_404(Item, pk=pk)
    
    # Check if item is used in any invoices
    if InvoiceItem.objects.filter(item=item).exists():
        messages.error(request, f'Cannot delete item that is used in invoices. Consider marking it as inactive instead.')
        return redirect('invoicing:item_list')
    
    if request.method == 'POST':
        item_name = item.name
        item.delete()
        messages.success(request, f'Item {item_name} deleted successfully.')
        return redirect('invoicing:item_list')
    
    context = {
        'title': f'Delete {item.get_item_type_display()}: {item.name}',
        'item': item,
    }
    return render(request, 'invoicing/item_confirm_delete.html', context)


@login_required
def template_list(request):
    """List invoice templates."""
    templates = InvoiceTemplate.objects.all()
    
    context = {
        'title': 'Invoice Templates',
        'templates': templates,
    }
    return render(request, 'invoicing/template_list.html', context)


@login_required
def template_create(request):
    """Create a new template."""
    if request.method == 'POST':
        form = InvoiceTemplateForm(request.POST, request.FILES)
        
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            
            messages.success(request, f'Template {template.name} created successfully.')
            return redirect('invoicing:template_list')
    else:
        form = InvoiceTemplateForm()
    
    context = {
        'title': 'Create Invoice Template',
        'form': form,
    }
    return render(request, 'invoicing/template_form.html', context)


@login_required
def template_edit(request, pk):
    """Edit a template."""
    template = get_object_or_404(InvoiceTemplate, pk=pk)
    
    if request.method == 'POST':
        form = InvoiceTemplateForm(request.POST, request.FILES, instance=template)
        
        if form.is_valid():
            form.save()
            messages.success(request, f'Template {template.name} updated successfully.')
            return redirect('invoicing:template_list')
    else:
        form = InvoiceTemplateForm(instance=template)
    
    context = {
        'title': f'Edit Template: {template.name}',
        'form': form,
        'template': template,
    }
    return render(request, 'invoicing/template_form.html', context)


@login_required
def template_delete(request, pk):
    """Delete a template."""
    template = get_object_or_404(InvoiceTemplate, pk=pk)
    
    # Check if template is being used
    if Invoice.objects.filter(template=template).exists():
        messages.error(request, f'Cannot delete template that is being used by invoices.')
        return redirect('invoicing:template_list')
    
    # Check if it's the default template in settings
    try:
        settings = Settings.objects.first()
        if settings and settings.default_template == template:
            messages.error(request, f'Cannot delete the default template. Change the default template in settings first.')
            return redirect('invoicing:template_list')
    except:
        pass
        
    if request.method == 'POST':
        template_name = template.name
        template.delete()
        messages.success(request, f'Template {template_name} deleted successfully.')
        return redirect('invoicing:template_list')
    
    context = {
        'title': f'Delete Template: {template.name}',
        'template': template,
    }
    return render(request, 'invoicing/template_confirm_delete.html', context)


@login_required
def template_set_default(request, pk):
    """Set a template as default."""
    template = get_object_or_404(InvoiceTemplate, pk=pk)
    
    template.is_default = True
    template.save()  # This will handle setting other templates to not default
    
    # Also update the settings
    try:
        settings = Settings.objects.first()
        if settings:
            settings.default_template = template
            settings.save()
    except:
        pass
    
    messages.success(request, f'Template {template.name} set as default.')
    return redirect('invoicing:template_list')


@login_required
def payment_list(request):
    """List all payments."""
    payments = Payment.objects.all().select_related('invoice', 'invoice__customer')
    
    # Filter by date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
    
    # Filter by payment method
    payment_method = request.GET.get('payment_method')
    if payment_method:
        payments = payments.filter(payment_method=payment_method)
    
    # Filter by customer
    customer_id = request.GET.get('customer')
    if customer_id:
        payments = payments.filter(invoice__customer_id=customer_id)
    
    # Order by
    order_by = request.GET.get('order_by', '-payment_date')
    payments = payments.order_by(order_by)
    
    # Calculate total
    total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'title': 'Payments',
        'payments': payments,
        'total_amount': total_amount,
        'date_from': date_from,
        'date_to': date_to,
        'payment_method': payment_method,
        'customer_id': customer_id,
        'customers': Customer.objects.all(),
    }
    return render(request, 'invoicing/payment_list.html', context)


@login_required
def settings_view(request):
    """Manage invoicing settings."""
    # Try to get existing settings or create new one
    try:
        settings = Settings.objects.first()
        if not settings:
            settings = Settings(company_name="Your Company")
    except:
        settings = Settings(company_name="Your Company")
    
    if request.method == 'POST':
        form = SettingsForm(request.POST, request.FILES, instance=settings)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings updated successfully.')
            return redirect('invoicing:settings')
    else:
        form = SettingsForm(instance=settings)
    
    context = {
        'title': 'Invoice Settings',
        'form': form,
        'settings': settings,
    }
    return render(request, 'invoicing/settings.html', context)


@login_required
def reports(request):
    """Reports dashboard."""
    context = {
        'title': 'Reports',
    }
    return render(request, 'invoicing/reports.html', context)


@login_required
def aging_report(request):
    """Accounts receivable aging report."""
    # Get all unpaid invoices
    invoices = Invoice.objects.exclude(status__in=['paid', 'cancelled'])
    
    # Filter by customer if specified
    customer_id = request.GET.get('customer')
    if customer_id:
        invoices = invoices.filter(customer_id=customer_id)
        
    today = timezone.now().date()
    
    # Classify invoices by age
    aging_buckets = {
        'current': [],
        '1_30': [],
        '31_60': [],
        '61_90': [],
        'over_90': []
    }
    
    for invoice in invoices:
        days_outstanding = (today - invoice.due_date).days if invoice.due_date < today else 0
        
        if days_outstanding <= 0:
            aging_buckets['current'].append(invoice)
        elif days_outstanding <= 30:
            aging_buckets['1_30'].append(invoice)
        elif days_outstanding <= 60:
            aging_buckets['31_60'].append(invoice)
        elif days_outstanding <= 90:
            aging_buckets['61_90'].append(invoice)
        else:
            aging_buckets['over_90'].append(invoice)
    
    # Calculate totals for each bucket
    totals = {
        'current': sum(inv.balance_due for inv in aging_buckets['current']),
        '1_30': sum(inv.balance_due for inv in aging_buckets['1_30']),
        '31_60': sum(inv.balance_due for inv in aging_buckets['31_60']),
        '61_90': sum(inv.balance_due for inv in aging_buckets['61_90']),
        'over_90': sum(inv.balance_due for inv in aging_buckets['over_90']),
    }
    totals['total'] = sum(totals.values())
    
    context = {
        'title': 'Accounts Receivable Aging',
        'aging_buckets': aging_buckets,
        'totals': totals,
        'customer_id': customer_id,
        'customers': Customer.objects.all(),
        'today_date': today.isoformat(),  # Add this line to make it available in the template
    }
    return render(request, 'invoicing/aging_report.html', context)


@login_required
def revenue_report(request):
    """Revenue report by period and category."""
    # Default to current year
    year = int(request.GET.get('year', timezone.now().year))
    
    # Get all paid invoices for the year
    invoices = Invoice.objects.filter(
        status='paid',
        issue_date__year=year
    )
    
    # Group by month
    monthly_revenue = {}
    for month in range(1, 13):
        month_invoices = invoices.filter(issue_date__month=month)
        monthly_revenue[month] = month_invoices.aggregate(total=Sum('total'))['total'] or 0
    
    # Calculate total for year
    yearly_total = sum(monthly_revenue.values())
    
    # Get data for chart (JSON format)
    chart_data = [
        {
            'month': datetime(year, month, 1).strftime('%b'),
            'amount': amount
        }
        for month, amount in monthly_revenue.items()
    ]
    
    # Add default date ranges for the filter
    today = timezone.now().date()
    first_day_of_year = date(year, 1, 1)
    
    context = {
        'title': 'Revenue Report',
        'year': year,
        'monthly_revenue': monthly_revenue,
        'yearly_total': yearly_total,
        'chart_data': json.dumps(chart_data),
        'years': range(timezone.now().year - 5, timezone.now().year + 1),
        'default_start_date': first_day_of_year.isoformat(),  # Add this line
        'default_end_date': today.isoformat(),               # Add this line
        'customers': Customer.objects.all(),                 # Add this if your template needs it
    }
    return render(request, 'invoicing/revenue_report.html', context)


@login_required
def customer_analysis(request):
    """Customer spending patterns and analysis report."""
    # Get date range parameters
    period = request.GET.get('period', 'this_year')
    
    # Set default date range based on selected period
    today = timezone.now().date()
    
    if period == 'this_month':
        start_date = date(today.year, today.month, 1)
        end_date = today
    elif period == 'last_month':
        last_month = today.month - 1 if today.month > 1 else 12
        last_month_year = today.year if today.month > 1 else today.year - 1
        start_date = date(last_month_year, last_month, 1)
        # Last day of last month
        if last_month == 12:
            end_date = date(last_month_year, 12, 31)
        else:
            end_date = date(last_month_year, last_month + 1, 1) - timedelta(days=1)
    elif period == 'this_quarter':
        current_quarter = (today.month - 1) // 3 + 1
        start_date = date(today.year, (current_quarter - 1) * 3 + 1, 1)
        end_date = today
    elif period == 'last_quarter':
        current_quarter = (today.month - 1) // 3 + 1
        last_quarter = current_quarter - 1 if current_quarter > 1 else 4
        last_quarter_year = today.year if current_quarter > 1 else today.year - 1
        start_date = date(last_quarter_year, (last_quarter - 1) * 3 + 1, 1)
        end_date = date(today.year, (current_quarter - 1) * 3 + 1, 1) - timedelta(days=1)
    elif period == 'this_year':
        start_date = date(today.year, 1, 1)
        end_date = today
    elif period == 'last_year':
        start_date = date(today.year - 1, 1, 1)
        end_date = date(today.year - 1, 12, 31)
    elif period == 'custom':
        # Use custom date range if provided
        try:
            start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date = date(today.year, 1, 1)
            end_date = today
    else:
        # Default to this year
        start_date = date(today.year, 1, 1)
        end_date = today
    
    # Get all paid invoices for the date range
    invoices = Invoice.objects.filter(
        status__in=['paid', 'partially_paid'],
        issue_date__gte=start_date,
        issue_date__lte=end_date
    )
    
    # Filter by customer type if specified
    customer_type = request.GET.get('customer_type')
    if customer_type:
        invoices = invoices.filter(customer__customer_type=customer_type)
    
    # Min revenue filter
    min_revenue = request.GET.get('min_revenue')
    
    # Get customer data
    customer_data = []
    total_revenue = 0
    
    # Get unique customers from invoices
    customers = Customer.objects.filter(invoices__in=invoices).distinct()
    
    for customer in customers:
        customer_invoices = invoices.filter(customer=customer)
        revenue = customer_invoices.aggregate(total=Sum('total'))['total'] or 0
        
        # Skip if revenue is below minimum
        if min_revenue and float(revenue) < float(min_revenue):
            continue
            
        invoice_count = customer_invoices.count()
        avg_invoice = revenue / invoice_count if invoice_count else 0
        
        # Get first and last purchase dates
        first_purchase = customer_invoices.order_by('issue_date').first()
        last_purchase = customer_invoices.order_by('-issue_date').first()
        
        customer_data.append({
            'id': customer.id,
            'name': f"{customer.first_name} {customer.last_name}",
            'company_name': customer.company_name,
            'customer_type': customer.customer_type,
            'revenue': revenue,
            'invoice_count': invoice_count,
            'avg_invoice': avg_invoice,
            'first_purchase': first_purchase.issue_date if first_purchase else None,
            'last_purchase': last_purchase.issue_date if last_purchase else None,
        })
        
        total_revenue += revenue
    
    # Sort data based on selected criterion
    sort_by = request.GET.get('sort_by', 'revenue')
    if sort_by == 'revenue':
        customer_data.sort(key=lambda x: x['revenue'], reverse=True)
    elif sort_by == 'invoice_count':
        customer_data.sort(key=lambda x: x['invoice_count'], reverse=True)
    elif sort_by == 'avg_invoice':
        customer_data.sort(key=lambda x: x['avg_invoice'], reverse=True)
    elif sort_by == 'recency':
        customer_data.sort(key=lambda x: x['last_purchase'] or date(1900, 1, 1), reverse=True)
    
    # Calculate percentages of total revenue
    for customer in customer_data:
        customer['percentage'] = (customer['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
    
    # Calculate business vs individual revenue
    business_revenue = sum(c['revenue'] for c in customer_data if c['customer_type'] == 'business')
    individual_revenue = sum(c['revenue'] for c in customer_data if c['customer_type'] == 'individual')
    
    # Calculate top 20% metrics
    active_customers = len(customer_data)
    top_20_percent_count = max(1, int(active_customers * 0.2))
    top_20_percent_revenue = sum(c['revenue'] for c in customer_data[:top_20_percent_count])
    top_20_percent_percentage = (top_20_percent_revenue / total_revenue * 100) if total_revenue > 0 else 0
    
    # Prepare Pareto analysis data
    pareto_data = []
    cumulative_revenue = 0
    segment_size = max(1, active_customers // 5)  # Split into 5 segments
    
    for i in range(0, active_customers, segment_size):
        segment = customer_data[i:i+segment_size]
        segment_revenue = sum(c['revenue'] for c in segment)
        cumulative_revenue += segment_revenue
        cumulative_percentage = (cumulative_revenue / total_revenue * 100) if total_revenue > 0 else 0
        
        pareto_data.append({
            'label': f"Top {i+1}-{min(i+segment_size, active_customers)}",
            'revenue': segment_revenue,
            'cumulative_percentage': cumulative_percentage
        })
    
    # Calculate average revenue per customer
    avg_revenue_per_customer = total_revenue / active_customers if active_customers > 0 else 0
    
    context = {
        'customer_data': customer_data,
        'total_revenue': total_revenue,
        'active_customers': active_customers,
        'avg_revenue_per_customer': avg_revenue_per_customer,
        'top_20_percent_revenue': top_20_percent_revenue,
        'top_20_percent_count': top_20_percent_count,
        'top_20_percent_percentage': top_20_percent_percentage,
        'business_revenue': business_revenue,
        'individual_revenue': individual_revenue,
        'pareto_data': pareto_data,
        'default_start_date': start_date.isoformat(),
        'default_end_date': end_date.isoformat(),
    }
    
    return render(request, 'invoicing/customer_analysis.html', context)


@login_required
def product_performance(request):
    """Product/service performance analysis report."""
    # Get date range parameters
    period = request.GET.get('period', 'this_year')
    
    # Set default date range based on selected period
    today = timezone.now().date()
    
    if period == 'this_month':
        start_date = date(today.year, today.month, 1)
        end_date = today
    elif period == 'last_month':
        last_month = today.month - 1 if today.month > 1 else 12
        last_month_year = today.year if today.month > 1 else today.year - 1
        start_date = date(last_month_year, last_month, 1)
        # Last day of last month
        if last_month == 12:
            end_date = date(last_month_year, 12, 31)
        else:
            end_date = date(last_month_year, last_month + 1, 1) - timedelta(days=1)
    elif period == 'this_quarter':
        current_quarter = (today.month - 1) // 3 + 1
        start_date = date(today.year, (current_quarter - 1) * 3 + 1, 1)
        end_date = today
    elif period == 'last_quarter':
        current_quarter = (today.month - 1) // 3 + 1
        last_quarter = current_quarter - 1 if current_quarter > 1 else 4
        last_quarter_year = today.year if current_quarter > 1 else today.year - 1
        start_date = date(last_quarter_year, (last_quarter - 1) * 3 + 1, 1)
        end_date = date(today.year, (current_quarter - 1) * 3 + 1, 1) - timedelta(days=1)
    elif period == 'this_year':
        start_date = date(today.year, 1, 1)
        end_date = today
    elif period == 'last_year':
        start_date = date(today.year - 1, 1, 1)
        end_date = date(today.year - 1, 12, 31)
    elif period == 'custom':
        # Use custom date range if provided
        try:
            start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date = date(today.year, 1, 1)
            end_date = today
    else:
        # Default to this year
        start_date = date(today.year, 1, 1)
        end_date = today
    
    # Get all paid invoices for the date range
    invoices = Invoice.objects.filter(
        status__in=['paid', 'partially_paid'],
        issue_date__gte=start_date,
        issue_date__lte=end_date
    )
    
    # Get all invoice items for these invoices
    invoice_items = InvoiceItem.objects.filter(invoice__in=invoices)
    
    # Filter by item type if specified
    item_type = request.GET.get('item_type')
    if item_type:
        invoice_items = invoice_items.filter(item__item_type=item_type)
    
    # Get product performance data
    product_data = []
    total_revenue = 0
    total_quantity = 0
    
    # Get unique items from invoice items
    items = {}
    
    for invoice_item in invoice_items:
        item_id = invoice_item.item_id if invoice_item.item_id else f"custom_{invoice_item.id}"
        item_name = invoice_item.item.name if invoice_item.item else invoice_item.description
        item_type = invoice_item.item.item_type if invoice_item.item else 'service'
        
        line_total = invoice_item.line_total
        quantity = invoice_item.quantity
        
        if item_id in items:
            items[item_id]['revenue'] += line_total
            items[item_id]['quantity'] += quantity
            items[item_id]['invoice_count'] += 1
        else:
            items[item_id] = {
                'id': invoice_item.item_id if invoice_item.item_id else None,
                'name': item_name,
                'item_type': item_type,
                'revenue': line_total,
                'quantity': quantity,
                'invoice_count': 1
            }
        
        total_revenue += line_total
        total_quantity += quantity
    
    # Convert dictionary to list
    for item_id, item_data in items.items():
        avg_price = item_data['revenue'] / item_data['quantity'] if item_data['quantity'] > 0 else 0
        
        product_data.append({
            'id': item_data['id'],
            'name': item_data['name'],
            'item_type': item_data['item_type'],
            'revenue': item_data['revenue'],
            'quantity': item_data['quantity'],
            'invoice_count': item_data['invoice_count'],
            'avg_price': avg_price,
        })
    
    # Sort data based on selected criterion
    sort_by = request.GET.get('sort_by', 'revenue')
    if sort_by == 'revenue':
        product_data.sort(key=lambda x: x['revenue'], reverse=True)
    elif sort_by == 'quantity':
        product_data.sort(key=lambda x: x['quantity'], reverse=True)
    elif sort_by == 'invoices':
        product_data.sort(key=lambda x: x['invoice_count'], reverse=True)
    
    # Calculate percentages of total revenue
    for product in product_data:
        product['percentage'] = (product['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
    
    # Calculate product vs service revenue
    product_revenue = sum(p['revenue'] for p in product_data if p['item_type'] == 'product')
    service_revenue = sum(p['revenue'] for p in product_data if p['item_type'] == 'service')
    
    # Get top 5 products for trend analysis
    top_5_products = product_data[:5]
    
    # Generate trend data for top 5 products
    # For simplicity, we'll just generate 6 periods (months)
    months = 6
    trend_periods = []
    top_5_trend = []
    
    # Generate period labels
    trend_date = end_date
    for i in range(months):
        trend_periods.insert(0, trend_date.strftime('%b %Y'))
        # Move to previous month
        if trend_date.month == 1:
            trend_date = date(trend_date.year - 1, 12, 1)
        else:
            trend_date = date(trend_date.year, trend_date.month - 1, 1)
    
    # Generate some colors for the chart
    colors = [
        'rgba(75, 192, 192, 1)',
        'rgba(153, 102, 255, 1)',
        'rgba(255, 159, 64, 1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 99, 132, 1)'
    ]
    
    # In a real application, you would query actual data for each period
    # For this demo, we'll generate some random data
    for i, product in enumerate(top_5_products):
        values = []
        base_revenue = product['revenue'] / 6  # Average monthly revenue
        
        for j in range(months):
            # Generate some variability for the trend
            # In a real app, you'd query actual data for each month
            factor = 0.7 + (j / months) * 0.6  # Simulate growth over time
            random_factor = 0.8 + random.random() * 0.4  # Random variability
            values.append(base_revenue * factor * random_factor)
        
        top_5_trend.append({
            'name': product['name'],
            'values': values,
            'color': colors[i % len(colors)]
        })
    
    # Calculate average unit price
    avg_unit_price = total_revenue / total_quantity if total_quantity > 0 else 0
    
    context = {
        'product_data': product_data,
        'total_revenue': total_revenue,
        'total_quantity': total_quantity,
        'unique_products': len(product_data),
        'avg_unit_price': avg_unit_price,
        'product_revenue': product_revenue,
        'service_revenue': service_revenue,
        'top_5_trend': top_5_trend,
        'trend_periods': trend_periods,
        'default_start_date': start_date.isoformat(),
        'default_end_date': end_date.isoformat(),
    }
    
    return render(request, 'invoicing/product_performance.html', context)


@login_required
def cash_flow(request):
    """Cash flow analysis report."""
    # Get date range parameters
    period = request.GET.get('period', 'this_year')
    
    # Set default date range based on selected period
    today = timezone.now().date()
    
    if period == 'this_month':
        start_date = date(today.year, today.month, 1)
        end_date = today
    elif period == 'last_month':
        last_month = today.month - 1 if today.month > 1 else 12
        last_month_year = today.year if today.month > 1 else today.year - 1
        start_date = date(last_month_year, last_month, 1)
        # Last day of last month
        if last_month == 12:
            end_date = date(last_month_year, 12, 31)
        else:
            end_date = date(last_month_year, last_month + 1, 1) - timedelta(days=1)
    elif period == 'this_quarter':
        current_quarter = (today.month - 1) // 3 + 1
        start_date = date(today.year, (current_quarter - 1) * 3 + 1, 1)
        end_date = today
    elif period == 'last_quarter':
        current_quarter = (today.month - 1) // 3 + 1
        last_quarter = current_quarter - 1 if current_quarter > 1 else 4
        last_quarter_year = today.year if current_quarter > 1 else today.year - 1
        start_date = date(last_quarter_year, (last_quarter - 1) * 3 + 1, 1)
        end_date = date(today.year, (current_quarter - 1) * 3 + 1, 1) - timedelta(days=1)
    elif period == 'this_year':
        start_date = date(today.year, 1, 1)
        end_date = today
    elif period == 'last_year':
        start_date = date(today.year - 1, 1, 1)
        end_date = date(today.year - 1, 12, 31)
    elif period == 'custom':
        # Use custom date range if provided
        try:
            start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date = date(today.year, 1, 1)
            end_date = today
    else:
        # Default to this year
        start_date = date(today.year, 1, 1)
        end_date = today
    
    # Get interval for grouping
    interval = request.GET.get('interval', 'monthly')
    
    # Get all payments for the date range (inflows)
    payments = Payment.objects.filter(
        payment_date__gte=start_date,
        payment_date__lte=end_date
    ).order_by('payment_date')
    
    # For this demo, we'll assume outflows are 0 since we don't track expenses
    # In a full accounting system, you would fetch expenses/outflows here
    
    # Prepare cash flow data based on interval
    cash_flow_data = []
    
    if interval == 'daily':
        # Group by day
        current_date = start_date
        while current_date <= end_date:
            day_payments = payments.filter(payment_date=current_date)
            inflow = day_payments.aggregate(total=Sum('amount'))['total'] or 0
            
            cash_flow_data.append({
                'date': current_date,
                'label': current_date.strftime('%b %d, %Y'),
                'inflow': inflow,
                'outflow': 0,  # No outflow data in this system
                'net_flow': inflow
            })
            
            current_date += timedelta(days=1)
    
    elif interval == 'weekly':
        # Group by week
        current_date = start_date
        while current_date <= end_date:
            # Calculate week end date
            week_end = min(current_date + timedelta(days=6), end_date)
            
            week_payments = payments.filter(payment_date__gte=current_date, payment_date__lte=week_end)
            inflow = week_payments.aggregate(total=Sum('amount'))['total'] or 0
            
            cash_flow_data.append({
                'date': current_date,
                'label': f"{current_date.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}",
                'inflow': inflow,
                'outflow': 0,  # No outflow data in this system
                'net_flow': inflow
            })
            
            current_date = week_end + timedelta(days=1)
    
    else:  # monthly
        # Group by month
        current_month = date(start_date.year, start_date.month, 1)
        while current_month <= end_date:
            # Calculate month end date
            if current_month.month == 12:
                next_month = date(current_month.year + 1, 1, 1)
            else:
                next_month = date(current_month.year, current_month.month + 1, 1)
            
            month_end = min(next_month - timedelta(days=1), end_date)
            
            month_payments = payments.filter(payment_date__gte=current_month, payment_date__lte=month_end)
            inflow = month_payments.aggregate(total=Sum('amount'))['total'] or 0
            
            cash_flow_data.append({
                'date': current_month,
                'label': current_month.strftime('%b %Y'),
                'inflow': inflow,
                'outflow': 0,  # No outflow data in this system
                'net_flow': inflow
            })
            
            # Move to next month
            if current_month.month == 12:
                current_month = date(current_month.year + 1, 1, 1)
            else:
                current_month = date(current_month.year, current_month.month + 1, 1)
    
    # Calculate cumulative cash flow
    cumulative = 0
    for period in cash_flow_data:
        cumulative += period['net_flow']
        period['cumulative'] = cumulative
    
    # Calculate totals
    total_inflow = sum(period['inflow'] for period in cash_flow_data)
    total_outflow = sum(period['outflow'] for period in cash_flow_data)
    net_cash_flow = total_inflow - total_outflow
    
    # For demonstration purposes, set current cash position
    # In a real app, this would be calculated from all historical data
    current_cash_position = 10000 + net_cash_flow  # Starting balance + net flow
    
    # Get upcoming inflows (unpaid invoices)
    upcoming_inflows = Invoice.objects.filter(
        status__in=['draft', 'sent', 'viewed', 'partially_paid', 'overdue'],
        due_date__gte=today
    ).order_by('due_date')[:10]  # Limit to 10 for demo
    
    # Get recent payments
    recent_payments = payments.order_by('-payment_date')[:10]  # Get latest 10 payments
    
    # Generate cash flow projections for next 6 months
    cash_flow_projections = []
    projection_date = today
    cumulative_balance = current_cash_position
    
    for i in range(6):
        # Calculate month end date
        if projection_date.month == 12:
            next_month = date(projection_date.year + 1, 1, 1)
        else:
            next_month = date(projection_date.year, projection_date.month + 1, 1)
        
        month_end = next_month - timedelta(days=1)
        
        # Get projected inflows for this month
        projected_invoices = Invoice.objects.filter(
            status__in=['draft', 'sent', 'viewed', 'partially_paid', 'overdue'],
            due_date__gte=projection_date,
            due_date__lte=month_end
        )
        
        projected_inflow = projected_invoices.aggregate(total=Sum('balance_due'))['total'] or 0
        
        # In a real app, you might apply a probability factor based on historical payment patterns
        # For demo purposes, we'll use a simple factor
        if i < 3:
            probability_factor = 0.9 - (i * 0.1)  # 90%, 80%, 70% for first 3 months
        else:
            probability_factor = 0.6 - ((i - 3) * 0.1)  # 60%, 50%, 40% for next 3 months
        
        adjusted_inflow = projected_inflow * probability_factor
        
        # Update cumulative balance
        cumulative_balance += adjusted_inflow
        
        cash_flow_projections.append({
            'label': projection_date.strftime('%b %Y'),
            'inflow': adjusted_inflow,
            'balance': cumulative_balance
        })
        
        # Move to next month
        if projection_date.month == 12:
            projection_date = date(projection_date.year + 1, 1, 1)
        else:
            projection_date = date(projection_date.year, projection_date.month + 1, 1)
    
    context = {
        'cash_flow_data': cash_flow_data,
        'total_inflow': total_inflow,
        'total_outflow': total_outflow,
        'net_cash_flow': net_cash_flow,
        'current_cash_position': current_cash_position,
        'upcoming_inflows': upcoming_inflows,
        'recent_payments': recent_payments,
        'cash_flow_projections': cash_flow_projections,
        'default_start_date': start_date.isoformat(),
        'default_end_date': end_date.isoformat(),
    }
    
    return render(request, 'invoicing/cash_flow.html', context)
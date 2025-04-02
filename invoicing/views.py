from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def home(request):
    """Invoicing module home page."""
    context = {
        'title': 'Invoicing',
        'total_invoices': 0,
        'pending_invoices': 0,
        'total_amount': 0.00
    }
    return render(request, 'invoicing/home.html', context)

@login_required
def invoice_list(request):
    """List all invoices."""
    context = {
        'title': 'Invoices',
        'invoices': []  # Will be replaced with actual queryset
    }
    return render(request, 'invoicing/invoice_list.html', context)

@login_required
def invoice_create(request):
    """Create a new invoice."""
    if request.method == 'POST':
        # Handle form submission (to be implemented)
        messages.success(request, 'Invoice created successfully.')
        return redirect('invoicing:invoice_list')
    
    context = {
        'title': 'Create Invoice',
        'customers': [],  # Will be replaced with actual queryset
        'templates': []   # Will be replaced with actual queryset
    }
    return render(request, 'invoicing/invoice_form.html', context)

@login_required
def invoice_detail(request, pk):
    """Display invoice details."""
    # invoice = get_object_or_404(Invoice, pk=pk)  # Will be implemented when model is created
    context = {
        'title': 'Invoice Details',
        # 'invoice': invoice
    }
    return render(request, 'invoicing/invoice_detail.html', context)

@login_required
def invoice_edit(request, pk):
    """Edit an invoice."""
    if request.method == 'POST':
        # Handle form submission (to be implemented)
        messages.success(request, 'Invoice updated successfully.')
        return redirect('invoicing:invoice_detail', pk=pk)
    
    context = {
        'title': 'Edit Invoice',
    }
    return render(request, 'invoicing/invoice_form.html', context)

@login_required
def invoice_delete(request, pk):
    """Delete an invoice."""
    if request.method == 'POST':
        # Handle deletion (to be implemented)
        messages.success(request, 'Invoice deleted successfully.')
        return redirect('invoicing:invoice_list')
    
    context = {
        'title': 'Delete Invoice',
    }
    return render(request, 'invoicing/invoice_confirm_delete.html', context)

@login_required
def invoice_send(request, pk):
    """Send invoice to customer."""
    if request.method == 'POST':
        # Handle sending invoice (to be implemented)
        messages.success(request, 'Invoice sent successfully.')
        return redirect('invoicing:invoice_detail', pk=pk)
    
    context = {
        'title': 'Send Invoice',
    }
    return render(request, 'invoicing/invoice_send.html', context)

@login_required
def customer_list(request):
    """List all customers."""
    context = {
        'title': 'Customers',
        'customers': []  # Will be replaced with actual queryset
    }
    return render(request, 'invoicing/customer_list.html', context)

@login_required
def customer_create(request):
    """Create a new customer."""
    if request.method == 'POST':
        # Handle form submission (to be implemented)
        messages.success(request, 'Customer created successfully.')
        return redirect('invoicing:customer_list')
    
    context = {
        'title': 'Add Customer',
    }
    return render(request, 'invoicing/customer_form.html', context)

@login_required
def customer_detail(request, pk):
    """Display customer details."""
    # customer = get_object_or_404(Customer, pk=pk)  # Will be implemented when model is created
    context = {
        'title': 'Customer Details',
        # 'customer': customer
    }
    return render(request, 'invoicing/customer_detail.html', context)

@login_required
def customer_edit(request, pk):
    """Edit customer information."""
    if request.method == 'POST':
        # Handle form submission (to be implemented)
        messages.success(request, 'Customer updated successfully.')
        return redirect('invoicing:customer_detail', pk=pk)
    
    context = {
        'title': 'Edit Customer',
    }
    return render(request, 'invoicing/customer_form.html', context)

@login_required
def settings(request):
    """Manage invoicing settings."""
    if request.method == 'POST':
        # Handle settings update (to be implemented)
        messages.success(request, 'Settings updated successfully.')
        return redirect('invoicing:settings')
    
    context = {
        'title': 'Invoice Settings',
    }
    return render(request, 'invoicing/settings.html', context)

@login_required
def template_list(request):
    """List invoice templates."""
    context = {
        'title': 'Invoice Templates',
        'templates': []  # Will be replaced with actual queryset
    }
    return render(request, 'invoicing/template_list.html', context)
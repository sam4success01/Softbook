from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def home(request):
    """Expenses module home page."""
    context = {
        'title': 'Expenses',
        'total_expenses': 0,
        'pending_approval': 0,
        'total_amount': 0.00
    }
    return render(request, 'expenses/home.html', context)

@login_required
def expense_list(request):
    """List all expenses."""
    context = {
        'title': 'Expenses',
        'expenses': []  # Will be replaced with actual queryset
    }
    return render(request, 'expenses/expense_list.html', context)

@login_required
def expense_create(request):
    """Create a new expense."""
    if request.method == 'POST':
        # Handle form submission (to be implemented)
        messages.success(request, 'Expense created successfully.')
        return redirect('expenses:expense_list')
    
    context = {
        'title': 'Add Expense',
        'categories': []  # Will be replaced with actual queryset
    }
    return render(request, 'expenses/expense_form.html', context)

@login_required
def expense_detail(request, pk):
    """Display expense details."""
    # expense = get_object_or_404(Expense, pk=pk)  # Will be implemented when model is created
    context = {
        'title': 'Expense Details',
        # 'expense': expense
    }
    return render(request, 'expenses/expense_detail.html', context)

@login_required
def expense_edit(request, pk):
    """Edit an expense."""
    if request.method == 'POST':
        # Handle form submission (to be implemented)
        messages.success(request, 'Expense updated successfully.')
        return redirect('expenses:expense_detail', pk=pk)
    
    context = {
        'title': 'Edit Expense',
    }
    return render(request, 'expenses/expense_form.html', context)

@login_required
def expense_delete(request, pk):
    """Delete an expense."""
    if request.method == 'POST':
        # Handle deletion (to be implemented)
        messages.success(request, 'Expense deleted successfully.')
        return redirect('expenses:expense_list')
    
    context = {
        'title': 'Delete Expense',
    }
    return render(request, 'expenses/expense_confirm_delete.html', context)

@login_required
def expense_approve(request, pk):
    """Approve or reject an expense."""
    if request.method == 'POST':
        # Handle approval/rejection (to be implemented)
        messages.success(request, 'Expense status updated successfully.')
        return redirect('expenses:expense_detail', pk=pk)
    
    context = {
        'title': 'Approve Expense',
    }
    return render(request, 'expenses/expense_approve.html', context)

@login_required
def category_list(request):
    """List expense categories."""
    context = {
        'title': 'Expense Categories',
        'categories': []  # Will be replaced with actual queryset
    }
    return render(request, 'expenses/category_list.html', context)

@login_required
def category_create(request):
    """Create a new expense category."""
    if request.method == 'POST':
        # Handle form submission (to be implemented)
        messages.success(request, 'Category created successfully.')
        return redirect('expenses:category_list')
    
    context = {
        'title': 'Add Category',
    }
    return render(request, 'expenses/category_form.html', context)

@login_required
def category_edit(request, pk):
    """Edit an expense category."""
    if request.method == 'POST':
        # Handle form submission (to be implemented)
        messages.success(request, 'Category updated successfully.')
        return redirect('expenses:category_list')
    
    context = {
        'title': 'Edit Category',
    }
    return render(request, 'expenses/category_form.html', context)

@login_required
def report_list(request):
    """List expense reports."""
    context = {
        'title': 'Expense Reports',
        'reports': []  # Will be replaced with actual queryset
    }
    return render(request, 'expenses/report_list.html', context)

@login_required
def generate_report(request):
    """Generate expense report."""
    if request.method == 'POST':
        # Handle report generation (to be implemented)
        messages.success(request, 'Report generated successfully.')
        return redirect('expenses:report_list')
    
    context = {
        'title': 'Generate Report',
    }
    return render(request, 'expenses/generate_report.html', context)

@login_required
def receipt_list(request):
    """List expense receipts."""
    context = {
        'title': 'Receipts',
        'receipts': []  # Will be replaced with actual queryset
    }
    return render(request, 'expenses/receipt_list.html', context)

@login_required
def receipt_upload(request):
    """Upload expense receipt."""
    if request.method == 'POST':
        # Handle receipt upload (to be implemented)
        messages.success(request, 'Receipt uploaded successfully.')
        return redirect('expenses:receipt_list')
    
    context = {
        'title': 'Upload Receipt',
    }
    return render(request, 'expenses/receipt_upload.html', context)
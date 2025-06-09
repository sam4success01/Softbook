# payables/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.urls import reverse
from datetime import date, datetime, timedelta
import json

from .models import (
    Vendor, Bill, BillItem, Expense, Payment, PaymentAllocation,
    PurchaseOrder, PurchaseOrderItem, ExpenseCategory, RecurringBill
)
from .forms import (
    VendorForm, BillForm, BillItemFormSet, ExpenseForm, PaymentForm,
    PaymentAllocationFormSet, PurchaseOrderForm, PurchaseOrderItemFormSet,
    ExpenseCategoryForm, RecurringBillForm, BillFilterForm, ExpenseFilterForm
)


@login_required
def home(request):
    """Payables module dashboard."""
    # Get statistics
    total_vendors = Vendor.objects.filter(is_active=True).count()
    
    # Outstanding bills
    outstanding_bills = Bill.objects.filter(
        status__in=['open', 'partially_paid', 'overdue']
    )
    total_outstanding = outstanding_bills.aggregate(total=Sum('balance_due'))['total'] or 0
    
    # This month's expenses
    current_month_start = timezone.now().date().replace(day=1)
    month_expenses = Expense.objects.filter(
        expense_date__gte=current_month_start
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Overdue bills
    today = timezone.now().date()
    overdue_bills = Bill.objects.filter(
        due_date__lt=today,
        status__in=['open', 'partially_paid']
    ).order_by('due_date')[:10]
    
    # Recent bills
    recent_bills = Bill.objects.all().order_by('-created_at')[:5]
    
    # Recent expenses
    recent_expenses = Expense.objects.all().order_by('-created_at')[:5]
    
    # Pending purchase orders
    pending_pos = PurchaseOrder.objects.filter(
        status__in=['draft', 'sent']
    ).count()
    
    # Upcoming recurring bills
    upcoming_recurring = RecurringBill.objects.filter(
        is_active=True,
        next_bill_date__lte=today + timedelta(days=7)
    ).order_by('next_bill_date')
    
    context = {
        'title': 'Payables Dashboard',
        'total_vendors': total_vendors,
        'total_outstanding': total_outstanding,
        'month_expenses': month_expenses,
        'overdue_bills': overdue_bills,
        'recent_bills': recent_bills,
        'recent_expenses': recent_expenses,
        'pending_pos': pending_pos,
        'upcoming_recurring': upcoming_recurring,
        'today': today,
    }
    return render(request, 'payables/home.html', context)


@login_required
def vendor_list(request):
    """List all vendors."""
    vendors = Vendor.objects.all()
    
    # Search functionality
    search_query = request.GET.get('q')
    if search_query:
        vendors = vendors.filter(
            Q(company_name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(tax_number__icontains=search_query)
        )
    
    # Filter by active status
    is_active = request.GET.get('is_active')
    if is_active in ['true', 'false']:
        vendors = vendors.filter(is_active=is_active == 'true')
    
    # Add statistics to each vendor
    for vendor in vendors:
        vendor.total_bills = vendor.bills.count()
        vendor.outstanding_amount = vendor.bills.filter(
            status__in=['open', 'partially_paid', 'overdue']
        ).aggregate(total=Sum('balance_due'))['total'] or 0
        vendor.total_purchases = vendor.bills.filter(
            status='paid'
        ).aggregate(total=Sum('total'))['total'] or 0
    
    # Pagination
    paginator = Paginator(vendors, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': 'Vendors',
        'vendors': page_obj,
        'search_query': search_query,
        'is_active': is_active,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }
    return render(request, 'payables/vendor_list.html', context)


@login_required
def vendor_create(request):
    """Create a new vendor."""
    if request.method == 'POST':
        form = VendorForm(request.POST)
        if form.is_valid():
            vendor = form.save(commit=False)
            vendor.created_by = request.user
            vendor.save()
            messages.success(request, f'Vendor {vendor.company_name} created successfully.')
            
            if 'save_and_new' in request.POST:
                return redirect('payables:vendor_create')
            else:
                return redirect('payables:vendor_detail', pk=vendor.pk)
    else:
        form = VendorForm()
    
    context = {
        'title': 'Add Vendor',
        'form': form,
    }
    return render(request, 'payables/vendor_form.html', context)


@login_required
def vendor_detail(request, pk):
    """Display vendor details."""
    vendor = get_object_or_404(Vendor, pk=pk)
    
    # Get vendor's bills
    bills = vendor.bills.all().order_by('-bill_date')[:10]
    
    # Get vendor's expenses
    expenses = vendor.expenses.all().order_by('-expense_date')[:10]
    
    # Get vendor's payments
    payments = vendor.payments.all().order_by('-payment_date')[:10]
    
    # Calculate statistics
    stats = {
        'total_bills': vendor.bills.count(),
        'open_bills': vendor.bills.filter(status__in=['open', 'overdue']).count(),
        'total_amount': vendor.bills.aggregate(total=Sum('total'))['total'] or 0,
        'paid_amount': vendor.bills.filter(status='paid').aggregate(total=Sum('total'))['total'] or 0,
        'outstanding_amount': vendor.get_outstanding_amount(),
        'total_expenses': vendor.expenses.count(),
        'expense_amount': vendor.expenses.aggregate(total=Sum('total_amount'))['total'] or 0,
    }
    
    context = {
        'title': f'Vendor: {vendor.company_name}',
        'vendor': vendor,
        'bills': bills,
        'expenses': expenses,
        'payments': payments,
        'stats': stats,
    }
    return render(request, 'payables/vendor_detail.html', context)


@login_required
def vendor_edit(request, pk):
    """Edit vendor information."""
    vendor = get_object_or_404(Vendor, pk=pk)
    
    if request.method == 'POST':
        form = VendorForm(request.POST, instance=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Vendor {vendor.company_name} updated successfully.')
            return redirect('payables:vendor_detail', pk=vendor.pk)
    else:
        form = VendorForm(instance=vendor)
    
    context = {
        'title': f'Edit Vendor: {vendor.company_name}',
        'form': form,
        'vendor': vendor,
        'is_edit': True,
    }
    return render(request, 'payables/vendor_form.html', context)


@login_required
def vendor_delete(request, pk):
    """Delete a vendor."""
    vendor = get_object_or_404(Vendor, pk=pk)
    
    # Check if vendor has related records
    if vendor.bills.exists() or vendor.expenses.exists() or vendor.payments.exists():
        messages.error(request, 'Cannot delete vendor with existing bills, expenses, or payments.')
        return redirect('payables:vendor_detail', pk=pk)
    
    if request.method == 'POST':
        vendor_name = vendor.company_name
        vendor.delete()
        messages.success(request, f'Vendor {vendor_name} deleted successfully.')
        return redirect('payables:vendor_list')
    
    context = {
        'title': f'Delete Vendor: {vendor.company_name}',
        'vendor': vendor,
    }
    return render(request, 'payables/vendor_confirm_delete.html', context)


@login_required
def bill_list(request):
    """List all bills with filtering."""
    # Get filter form
    filter_form = BillFilterForm(request.GET)
    
    # Base queryset
    bills = Bill.objects.all().select_related('vendor')
    
    # Apply filters
    if filter_form.is_valid():
        filters = filter_form.cleaned_data
        
        if filters.get('vendor'):
            bills = bills.filter(vendor=filters['vendor'])
            
        if filters.get('status'):
            bills = bills.filter(status=filters['status'])
            
        if filters.get('date_from'):
            bills = bills.filter(bill_date__gte=filters['date_from'])
            
        if filters.get('date_to'):
            bills = bills.filter(bill_date__lte=filters['date_to'])
            
        if filters.get('min_amount'):
            bills = bills.filter(total__gte=filters['min_amount'])
            
        if filters.get('max_amount'):
            bills = bills.filter(total__lte=filters['max_amount'])
    
    # Order by
    order_by = request.GET.get('order_by', '-bill_date')
    bills = bills.order_by(order_by)
    
    # Pagination
    paginator = Paginator(bills, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate totals
    total_amount = bills.aggregate(total=Sum('total'))['total'] or 0
    paid_amount = bills.aggregate(total=Sum('amount_paid'))['total'] or 0
    pending_amount = bills.aggregate(total=Sum('balance_due'))['total'] or 0
    
    context = {
        'title': 'Bills',
        'bills': page_obj,
        'filter_form': filter_form,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }
    return render(request, 'payables/bill_list.html', context)


@login_required
def bill_create(request):
    """Create a new bill."""
    if request.method == 'POST':
        form = BillForm(request.POST, request.FILES)
        formset = BillItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            # Save bill
            bill = form.save(commit=False)
            bill.created_by = request.user
            
            # Initialize totals for new bill
            bill.subtotal = 0
            bill.tax_amount = 0
            bill.total = bill.discount_amount or 0
            bill.balance_due = bill.total
            bill.save()
            
            # Save bill items
            items = formset.save(commit=False)
            for item in items:
                item.bill = bill
                item.save()
            
            # Handle deletions
            for item in formset.deleted_objects:
                item.delete()
            
            # Force recalculation
            bill.save()
            
            messages.success(request, f'Bill #{bill.bill_number} created successfully.')
            
            if 'save_and_new' in request.POST:
                return redirect('payables:bill_create')
            else:
                return redirect('payables:bill_detail', pk=bill.pk)
    else:
        # Set initial values
        initial = {
            'bill_date': timezone.now().date(),
            'status': 'open',
        }
        
        # If vendor is specified in URL
        vendor_id = request.GET.get('vendor')
        if vendor_id:
            try:
                vendor = Vendor.objects.get(pk=vendor_id)
                initial['vendor'] = vendor
                initial['due_date'] = timezone.now().date() + timedelta(days=vendor.get_payment_terms_days())
            except Vendor.DoesNotExist:
                pass
        
        form = BillForm(initial=initial)
        formset = BillItemFormSet()
    
    # Get expense categories for JavaScript
    categories = []
    for category in ExpenseCategory.objects.filter(is_active=True):
        categories.append({
            'id': category.id,
            'name': str(category),
            'description': category.description or '',
        })
    
    context = {
        'title': 'Create Bill',
        'form': form,
        'formset': formset,
        'categories': json.dumps(categories),
    }
    return render(request, 'payables/bill_form.html', context)


@login_required
def bill_detail(request, pk):
    """Display bill details."""
    bill = get_object_or_404(Bill, pk=pk)
    items = bill.items.all()
    payments = bill.payment_allocations.all()
    
    context = {
        'title': f'Bill #{bill.bill_number}',
        'bill': bill,
        'items': items,
        'payments': payments,
    }
    return render(request, 'payables/bill_detail.html', context)


@login_required
def bill_edit(request, pk):
    """Edit a bill."""
    bill = get_object_or_404(Bill, pk=pk)
    
    # Don't allow editing paid or cancelled bills
    if bill.status in ['paid', 'cancelled']:
        messages.error(request, f'Cannot edit bill in {bill.status} status.')
        return redirect('payables:bill_detail', pk=pk)
    
    if request.method == 'POST':
        form = BillForm(request.POST, request.FILES, instance=bill)
        formset = BillItemFormSet(request.POST, instance=bill)
        
        if form.is_valid() and formset.is_valid():
            bill = form.save()
            
            # Save formset items
            items = formset.save(commit=False)
            for item in items:
                item.bill = bill
                item.save()
            
            # Handle deletions
            for item in formset.deleted_objects:
                item.delete()
            
            # Force recalculation
            bill.save()
            
            messages.success(request, f'Bill #{bill.bill_number} updated successfully.')
            return redirect('payables:bill_detail', pk=bill.pk)
    else:
        form = BillForm(instance=bill)
        formset = BillItemFormSet(instance=bill)
    
    # Get expense categories for JavaScript
    categories = []
    for category in ExpenseCategory.objects.filter(is_active=True):
        categories.append({
            'id': category.id,
            'name': str(category),
            'description': category.description or '',
        })
    
    context = {
        'title': f'Edit Bill #{bill.bill_number}',
        'form': form,
        'formset': formset,
        'bill': bill,
        'categories': json.dumps(categories),
        'is_edit': True,
    }
    return render(request, 'payables/bill_form.html', context)


@login_required
def bill_delete(request, pk):
    """Delete a bill."""
    bill = get_object_or_404(Bill, pk=pk)
    
    # Don't allow deletion if payments exist
    if bill.payment_allocations.exists():
        messages.error(request, 'Cannot delete bill with payments. Cancel it instead.')
        return redirect('payables:bill_detail', pk=pk)
    
    if request.method == 'POST':
        bill_number = bill.bill_number
        bill.delete()
        messages.success(request, f'Bill #{bill_number} deleted successfully.')
        return redirect('payables:bill_list')
    
    context = {
        'title': f'Delete Bill #{bill.bill_number}',
        'bill': bill,
    }
    return render(request, 'payables/bill_confirm_delete.html', context)


# Continue payables/views.py

@login_required
def record_payment(request, pk):
    """Record payment for a bill."""
    bill = get_object_or_404(Bill, pk=pk)
    
    if bill.status == 'cancelled':
        messages.error(request, 'Cannot record payment for cancelled bill.')
        return redirect('payables:bill_detail', pk=pk)
    
    if request.method == 'POST':
        # Create payment
        payment = Payment(
            vendor=bill.vendor,
            payment_date=request.POST.get('payment_date'),
            amount=request.POST.get('amount'),
            payment_method=request.POST.get('payment_method'),
            reference_number=request.POST.get('reference_number'),
            notes=request.POST.get('notes'),
            created_by=request.user
        )
        payment.save()
        
        # Create payment allocation
        PaymentAllocation.objects.create(
            payment=payment,
            bill=bill,
            amount=payment.amount
        )
        
        messages.success(request, f'Payment of ${payment.amount} recorded successfully.')
        return redirect('payables:bill_detail', pk=pk)
    
    context = {
        'title': f'Record Payment for Bill #{bill.bill_number}',
        'bill': bill,
        'max_amount': bill.balance_due,
        'today': timezone.now().date(),
    }
    return render(request, 'payables/record_payment.html', context)


@login_required
def convert_to_expense(request, pk):
    """Convert a bill to expense."""
    bill = get_object_or_404(Bill, pk=pk)
    
    if request.method == 'POST':
        # Create expense from bill
        expense = Expense(
            vendor=bill.vendor,
            expense_date=bill.bill_date,
            category=bill.items.first().expense_category if bill.items.exists() else None,
            amount=bill.subtotal,
            tax_amount=bill.tax_amount,
            description=f"Converted from Bill #{bill.bill_number}",
            payment_mode='other',
            status='recorded',
            created_by=request.user
        )
        expense.save()
        
        # Mark bill as cancelled
        bill.status = 'cancelled'
        bill.save()
        
        messages.success(request, f'Bill converted to Expense #{expense.expense_number} successfully.')
        return redirect('payables:expense_detail', pk=expense.pk)
    
    context = {
        'title': f'Convert Bill #{bill.bill_number} to Expense',
        'bill': bill,
    }
    return render(request, 'payables/convert_to_expense.html', context)


@login_required
def expense_list(request):
    """List all expenses with filtering."""
    filter_form = ExpenseFilterForm(request.GET)
    
    expenses = Expense.objects.all().select_related('vendor', 'category')
    
    # Apply filters
    if filter_form.is_valid():
        filters = filter_form.cleaned_data
        
        if filters.get('vendor'):
            expenses = expenses.filter(vendor=filters['vendor'])
            
        if filters.get('category'):
            expenses = expenses.filter(category=filters['category'])
            
        if filters.get('status'):
            expenses = expenses.filter(status=filters['status'])
            
        if filters.get('date_from'):
            expenses = expenses.filter(expense_date__gte=filters['date_from'])
            
        if filters.get('date_to'):
            expenses = expenses.filter(expense_date__lte=filters['date_to'])
            
        if filters.get('is_billable'):
            expenses = expenses.filter(is_billable=filters['is_billable'] == 'true')
    
    # Order by
    order_by = request.GET.get('order_by', '-expense_date')
    expenses = expenses.order_by(order_by)
    
    # Pagination
    paginator = Paginator(expenses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate totals
    total_amount = expenses.aggregate(total=Sum('total_amount'))['total'] or 0
    
    context = {
        'title': 'Expenses',
        'expenses': page_obj,
        'filter_form': filter_form,
        'total_amount': total_amount,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }
    return render(request, 'payables/expense_list.html', context)


@login_required
def expense_create(request):
    """Create a new expense."""
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            
            messages.success(request, f'Expense #{expense.expense_number} created successfully.')
            
            if 'save_and_new' in request.POST:
                return redirect('payables:expense_create')
            else:
                return redirect('payables:expense_detail', pk=expense.pk)
    else:
        initial = {
            'expense_date': timezone.now().date(),
            'status': 'recorded',
        }
        form = ExpenseForm(initial=initial)
    
    context = {
        'title': 'Create Expense',
        'form': form,
    }
    return render(request, 'payables/expense_form.html', context)


@login_required
def expense_detail(request, pk):
    """Display expense details."""
    expense = get_object_or_404(Expense, pk=pk)
    
    context = {
        'title': f'Expense #{expense.expense_number}',
        'expense': expense,
    }
    return render(request, 'payables/expense_detail.html', context)


@login_required
def expense_edit(request, pk):
    """Edit an expense."""
    expense = get_object_or_404(Expense, pk=pk)
    
    if expense.status in ['approved', 'reimbursed']:
        messages.error(request, f'Cannot edit expense in {expense.status} status.')
        return redirect('payables:expense_detail', pk=pk)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, f'Expense #{expense.expense_number} updated successfully.')
            return redirect('payables:expense_detail', pk=expense.pk)
    else:
        form = ExpenseForm(instance=expense)
    
    context = {
        'title': f'Edit Expense #{expense.expense_number}',
        'form': form,
        'expense': expense,
        'is_edit': True,
    }
    return render(request, 'payables/expense_form.html', context)


@login_required
def expense_delete(request, pk):
    """Delete an expense."""
    expense = get_object_or_404(Expense, pk=pk)
    
    if expense.status in ['approved', 'reimbursed']:
        messages.error(request, f'Cannot delete expense in {expense.status} status.')
        return redirect('payables:expense_detail', pk=pk)
    
    if request.method == 'POST':
        expense_number = expense.expense_number
        expense.delete()
        messages.success(request, f'Expense #{expense_number} deleted successfully.')
        return redirect('payables:expense_list')
    
    context = {
        'title': f'Delete Expense #{expense.expense_number}',
        'expense': expense,
    }
    return render(request, 'payables/expense_confirm_delete.html', context)


@login_required
def expense_approve(request, pk):
    """Approve an expense."""
    expense = get_object_or_404(Expense, pk=pk)
    
    if expense.status != 'pending':
        messages.error(request, 'Only pending expenses can be approved.')
        return redirect('payables:expense_detail', pk=pk)
    
    expense.status = 'approved'
    expense.save()
    
    messages.success(request, f'Expense #{expense.expense_number} approved successfully.')
    return redirect('payables:expense_detail', pk=pk)


@login_required
def expense_reject(request, pk):
    """Reject an expense."""
    expense = get_object_or_404(Expense, pk=pk)
    
    if expense.status != 'pending':
        messages.error(request, 'Only pending expenses can be rejected.')
        return redirect('payables:expense_detail', pk=pk)
    
    expense.status = 'rejected'
    expense.save()
    
    messages.success(request, f'Expense #{expense.expense_number} rejected.')
    return redirect('payables:expense_detail', pk=pk)


@login_required
def payment_list(request):
    """List all payments."""
    payments = Payment.objects.all().select_related('vendor')
    
    # Filter by date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
    
    # Filter by vendor
    vendor_id = request.GET.get('vendor')
    if vendor_id:
        payments = payments.filter(vendor_id=vendor_id)
    
    # Order by
    order_by = request.GET.get('order_by', '-payment_date')
    payments = payments.order_by(order_by)
    
    # Pagination
    paginator = Paginator(payments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate total
    total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'title': 'Payments',
        'payments': page_obj,
        'total_amount': total_amount,
        'date_from': date_from,
        'date_to': date_to,
        'vendor_id': vendor_id,
        'vendors': Vendor.objects.all(),
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }
    return render(request, 'payables/payment_list.html', context)


@login_required
def payment_create(request):
    """Create a new payment."""
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        formset = PaymentAllocationFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            payment = form.save(commit=False)
            payment.created_by = request.user
            payment.save()
            
            # Save allocations
            allocations = formset.save(commit=False)
            for allocation in allocations:
                allocation.payment = payment
                allocation.save()
            
            # Handle deletions
            for allocation in formset.deleted_objects:
                allocation.delete()
            
            messages.success(request, f'Payment #{payment.payment_number} created successfully.')
            return redirect('payables:payment_detail', pk=payment.pk)
    else:
        initial = {
            'payment_date': timezone.now().date(),
        }
        
        # If vendor is specified
        vendor_id = request.GET.get('vendor')
        if vendor_id:
            try:
                vendor = Vendor.objects.get(pk=vendor_id)
                initial['vendor'] = vendor
            except Vendor.DoesNotExist:
                pass
        
        form = PaymentForm(initial=initial)
        formset = PaymentAllocationFormSet()
    
    context = {
        'title': 'Create Payment',
        'form': form,
        'formset': formset,
    }
    return render(request, 'payables/payment_form.html', context)


@login_required
def payment_detail(request, pk):
    """Display payment details."""
    payment = get_object_or_404(Payment, pk=pk)
    allocations = payment.allocations.all()
    
    context = {
        'title': f'Payment #{payment.payment_number}',
        'payment': payment,
        'allocations': allocations,
    }
    return render(request, 'payables/payment_detail.html', context)


@login_required
def payment_edit(request, pk):
    """Edit a payment."""
    payment = get_object_or_404(Payment, pk=pk)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        formset = PaymentAllocationFormSet(request.POST, instance=payment)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            
            # Save allocations
            allocations = formset.save(commit=False)
            for allocation in allocations:
                allocation.payment = payment
                allocation.save()
            
            # Handle deletions
            for allocation in formset.deleted_objects:
                allocation.delete()
            
            messages.success(request, f'Payment #{payment.payment_number} updated successfully.')
            return redirect('payables:payment_detail', pk=payment.pk)
    else:
        form = PaymentForm(instance=payment)
        formset = PaymentAllocationFormSet(instance=payment)
    
    context = {
        'title': f'Edit Payment #{payment.payment_number}',
        'form': form,
        'formset': formset,
        'payment': payment,
        'is_edit': True,
    }
    return render(request, 'payables/payment_form.html', context)


@login_required
def payment_delete(request, pk):
    """Delete a payment."""
    payment = get_object_or_404(Payment, pk=pk)
    
    if request.method == 'POST':
        payment_number = payment.payment_number
        
        # Delete allocations first (handled by cascade)
        payment.delete()
        
        messages.success(request, f'Payment #{payment_number} deleted successfully.')
        return redirect('payables:payment_list')
    
    context = {
        'title': f'Delete Payment #{payment.payment_number}',
        'payment': payment,
    }
    return render(request, 'payables/payment_confirm_delete.html', context)


# Continue payables/views.py

@login_required
def po_list(request):
    """List all purchase orders."""
    pos = PurchaseOrder.objects.all().select_related('vendor')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        pos = pos.filter(status=status)
    
    # Filter by vendor
    vendor_id = request.GET.get('vendor')
    if vendor_id:
        pos = pos.filter(vendor_id=vendor_id)
    
    # Order by
    order_by = request.GET.get('order_by', '-po_date')
    pos = pos.order_by(order_by)
    
    # Pagination
    paginator = Paginator(pos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': 'Purchase Orders',
        'purchase_orders': page_obj,
        'status': status,
        'vendor_id': vendor_id,
        'vendors': Vendor.objects.all(),
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }
    return render(request, 'payables/po_list.html', context)


@login_required
def po_create(request):
    """Create a new purchase order."""
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            po = form.save(commit=False)
            po.created_by = request.user
            
            # Initialize totals
            po.subtotal = 0
            po.tax_amount = 0
            po.total = po.discount_amount or 0
            po.save()
            
            # Save items
            items = formset.save(commit=False)
            for item in items:
                item.purchase_order = po
                item.save()
            
            # Handle deletions
            for item in formset.deleted_objects:
                item.delete()
            
            # Force recalculation
            po.save()
            
            messages.success(request, f'Purchase Order #{po.po_number} created successfully.')
            
            if 'save_and_send' in request.POST:
                return redirect('payables:po_send', pk=po.pk)
            else:
                return redirect('payables:po_detail', pk=po.pk)
    else:
        initial = {
            'po_date': timezone.now().date(),
            'status': 'draft',
        }
        form = PurchaseOrderForm(initial=initial)
        formset = PurchaseOrderItemFormSet()
    
    context = {
        'title': 'Create Purchase Order',
        'form': form,
        'formset': formset,
    }
    return render(request, 'payables/po_form.html', context)


@login_required
def po_detail(request, pk):
    """Display purchase order details."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    items = po.items.all()
    
    context = {
        'title': f'Purchase Order #{po.po_number}',
        'po': po,
        'items': items,
    }
    return render(request, 'payables/po_detail.html', context)


@login_required
def po_edit(request, pk):
    """Edit a purchase order."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    
    if po.status in ['billed', 'cancelled']:
        messages.error(request, f'Cannot edit purchase order in {po.status} status.')
        return redirect('payables:po_detail', pk=pk)
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=po)
        formset = PurchaseOrderItemFormSet(request.POST, instance=po)
        
        if form.is_valid() and formset.is_valid():
            po = form.save()
            
            # Save items
            items = formset.save(commit=False)
            for item in items:
                item.purchase_order = po
                item.save()
            
            # Handle deletions
            for item in formset.deleted_objects:
                item.delete()
            
            # Force recalculation
            po.save()
            
            messages.success(request, f'Purchase Order #{po.po_number} updated successfully.')
            return redirect('payables:po_detail', pk=po.pk)
    else:
        form = PurchaseOrderForm(instance=po)
        formset = PurchaseOrderItemFormSet(instance=po)
    
    context = {
        'title': f'Edit Purchase Order #{po.po_number}',
        'form': form,
        'formset': formset,
        'po': po,
        'is_edit': True,
    }
    return render(request, 'payables/po_form.html', context)


@login_required
def po_delete(request, pk):
    """Delete a purchase order."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    
    if po.status == 'billed':
        messages.error(request, 'Cannot delete purchase order that has been billed.')
        return redirect('payables:po_detail', pk=pk)
    
    if request.method == 'POST':
        po_number = po.po_number
        po.delete()
        messages.success(request, f'Purchase Order #{po_number} deleted successfully.')
        return redirect('payables:po_list')
    
    context = {
        'title': f'Delete Purchase Order #{po.po_number}',
        'po': po,
    }
    return render(request, 'payables/po_confirm_delete.html', context)


@login_required
def po_convert_to_bill(request, pk):
    """Convert purchase order to bill."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    
    if po.status == 'billed':
        messages.error(request, 'Purchase order has already been converted to bill.')
        return redirect('payables:po_detail', pk=pk)
    
    if request.method == 'POST':
        # Create bill from PO
        bill = Bill(
            vendor=po.vendor,
            bill_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=po.vendor.get_payment_terms_days()),
            status='open',
            discount_amount=po.discount_amount,
            notes=f"Created from Purchase Order #{po.po_number}",
            created_by=request.user
        )
        bill.save()
        
        # Copy items
        for po_item in po.items.all():
            BillItem.objects.create(
                bill=bill,
                expense_category_id=request.POST.get(f'category_{po_item.id}'),
                description=po_item.description or po_item.item_name,
                quantity=po_item.quantity,
                unit_price=po_item.unit_price,
                tax_rate=po_item.tax_rate
            )
        
        # Update PO status
        po.status = 'billed'
        po.save()
        
        messages.success(request, f'Purchase Order converted to Bill #{bill.bill_number} successfully.')
        return redirect('payables:bill_detail', pk=bill.pk)
    
    context = {
        'title': f'Convert PO #{po.po_number} to Bill',
        'po': po,
        'categories': ExpenseCategory.objects.filter(is_active=True),
    }
    return render(request, 'payables/po_convert_to_bill.html', context)


@login_required
def po_send(request, pk):
    """Send purchase order to vendor."""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    
    if request.method == 'POST':
        # In a real system, you would send an email here
        # For now, just update status
        if po.status == 'draft':
            po.status = 'sent'
            po.save()
        
        messages.success(request, f'Purchase Order #{po.po_number} sent to {po.vendor.email}.')
        return redirect('payables:po_detail', pk=pk)
    
    context = {
        'title': f'Send Purchase Order #{po.po_number}',
        'po': po,
    }
    return render(request, 'payables/po_send.html', context)


@login_required
def category_list(request):
    """List expense categories."""
    categories = ExpenseCategory.objects.all()
    
    context = {
        'title': 'Expense Categories',
        'categories': categories,
    }
    return render(request, 'payables/category_list.html', context)


@login_required
def category_create(request):
    """Create expense category."""
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense category created successfully.')
            return redirect('payables:category_list')
    else:
        form = ExpenseCategoryForm()
    
    context = {
        'title': 'Create Expense Category',
        'form': form,
    }
    return render(request, 'payables/category_form.html', context)


@login_required
def category_edit(request, pk):
    """Edit expense category."""
    category = get_object_or_404(ExpenseCategory, pk=pk)
    
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense category updated successfully.')
            return redirect('payables:category_list')
    else:
        form = ExpenseCategoryForm(instance=category)
    
    context = {
        'title': f'Edit Category: {category.name}',
        'form': form,
        'category': category,
        'is_edit': True,
    }
    return render(request, 'payables/category_form.html', context)


@login_required
def category_delete(request, pk):
    """Delete expense category."""
    category = get_object_or_404(ExpenseCategory, pk=pk)
    
    # Check if category is being used
    if BillItem.objects.filter(expense_category=category).exists() or Expense.objects.filter(category=category).exists():
        messages.error(request, 'Cannot delete category that is being used.')
        return redirect('payables:category_list')
    
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Expense category deleted successfully.')
        return redirect('payables:category_list')
    
    context = {
        'title': f'Delete Category: {category.name}',
        'category': category,
    }
    return render(request, 'payables/category_confirm_delete.html', context)


@login_required
def recurring_list(request):
    """List recurring bills."""
    recurring_bills = RecurringBill.objects.all().select_related('vendor', 'category')
    
    context = {
        'title': 'Recurring Bills',
        'recurring_bills': recurring_bills,
    }
    return render(request, 'payables/recurring_list.html', context)


@login_required
def recurring_create(request):
    """Create recurring bill."""
    if request.method == 'POST':
        form = RecurringBillForm(request.POST)
        if form.is_valid():
            recurring = form.save(commit=False)
            recurring.created_by = request.user
            recurring.next_bill_date = recurring.start_date
            recurring.save()
            
            messages.success(request, 'Recurring bill created successfully.')
            return redirect('payables:recurring_detail', pk=recurring.pk)
    else:
        form = RecurringBillForm()
    
    context = {
        'title': 'Create Recurring Bill',
        'form': form,
    }
    return render(request, 'payables/recurring_form.html', context)


@login_required
def recurring_detail(request, pk):
    """Display recurring bill details."""
    recurring = get_object_or_404(RecurringBill, pk=pk)
    
    # Get bills created from this recurring template
    bills = Bill.objects.filter(
        notes__contains=f"Generated from recurring bill: {recurring.name}"
    ).order_by('-bill_date')[:10]
    
    context = {
        'title': f'Recurring Bill: {recurring.name}',
        'recurring': recurring,
        'bills': bills,
    }
    return render(request, 'payables/recurring_detail.html', context)


@login_required
def recurring_edit(request, pk):
    """Edit recurring bill."""
    recurring = get_object_or_404(RecurringBill, pk=pk)
    
    if request.method == 'POST':
        form = RecurringBillForm(request.POST, instance=recurring)
        if form.is_valid():
            form.save()
            messages.success(request, 'Recurring bill updated successfully.')
            return redirect('payables:recurring_detail', pk=recurring.pk)
    else:
        form = RecurringBillForm(instance=recurring)
    
    context = {
        'title': f'Edit Recurring Bill: {recurring.name}',
        'form': form,
        'recurring': recurring,
        'is_edit': True,
    }
    return render(request, 'payables/recurring_form.html', context)


@login_required
def recurring_delete(request, pk):
    """Delete recurring bill."""
    recurring = get_object_or_404(RecurringBill, pk=pk)
    
    if request.method == 'POST':
        recurring.delete()
        messages.success(request, 'Recurring bill deleted successfully.')
        return redirect('payables:recurring_list')
    
    context = {
        'title': f'Delete Recurring Bill: {recurring.name}',
        'recurring': recurring,
    }
    return render(request, 'payables/recurring_confirm_delete.html', context)


@login_required
def recurring_create_bill(request, pk):
    """Manually create bill from recurring template."""
    recurring = get_object_or_404(RecurringBill, pk=pk)
    
    if request.method == 'POST':
        bill = recurring.create_bill()
        messages.success(request, f'Bill #{bill.bill_number} created from recurring template.')
        return redirect('payables:bill_detail', pk=bill.pk)
    
    context = {
        'title': f'Create Bill from: {recurring.name}',
        'recurring': recurring,
    }
    return render(request, 'payables/recurring_create_bill.html', context)


# Reports
@login_required
def reports(request):
    """Reports dashboard."""
    context = {
        'title': 'Payables Reports',
    }
    return render(request, 'payables/reports.html', context)


@login_required
def payables_summary(request):
    """Payables summary report."""
    # Get date range
    today = timezone.now().date()
    start_date = request.GET.get('start_date', today.replace(day=1))
    end_date = request.GET.get('end_date', today)
    
    # Get bills data
    bills = Bill.objects.filter(
        bill_date__gte=start_date,
        bill_date__lte=end_date
    )
    
    # Get expenses data
    expenses = Expense.objects.filter(
        expense_date__gte=start_date,
        expense_date__lte=end_date
    )
    
    # Calculate summaries
    summary = {
        'bills': {
            'count': bills.count(),
            'total': bills.aggregate(total=Sum('total'))['total'] or 0,
            'paid': bills.filter(status='paid').aggregate(total=Sum('total'))['total'] or 0,
            'outstanding': bills.exclude(status__in=['paid', 'cancelled']).aggregate(total=Sum('balance_due'))['total'] or 0,
        },
        'expenses': {
            'count': expenses.count(),
            'total': expenses.aggregate(total=Sum('total_amount'))['total'] or 0,
            'by_category': {},
        }
    }
    
    # Group expenses by category
    category_expenses = expenses.values('category__name').annotate(
        count=Count('id'),
        total=Sum('total_amount')
    ).order_by('-total')
    
    for cat in category_expenses:
        summary['expenses']['by_category'][cat['category__name']] = {
            'count': cat['count'],
            'total': cat['total']
        }
    
    context = {
        'title': 'Payables Summary',
        'summary': summary,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'payables/reports/payables_summary.html', context)


@login_required
def vendor_balance(request):
    """Vendor balance report."""
    vendors = Vendor.objects.filter(is_active=True)
    
    vendor_data = []
    for vendor in vendors:
        bills = vendor.bills.exclude(status='cancelled')
        
        data = {
            'vendor': vendor,
            'total_bills': bills.count(),
            'total_amount': bills.aggregate(total=Sum('total'))['total'] or 0,
            'paid_amount': bills.aggregate(total=Sum('amount_paid'))['total'] or 0,
            'outstanding': bills.exclude(status='paid').aggregate(total=Sum('balance_due'))['total'] or 0,
        }
        
        if data['outstanding'] > 0:
            vendor_data.append(data)
    
    # Sort by outstanding amount
    vendor_data.sort(key=lambda x: x['outstanding'], reverse=True)
    
    context = {
        'title': 'Vendor Balance Report',
        'vendor_data': vendor_data,
        'total_outstanding': sum(v['outstanding'] for v in vendor_data),
    }
    return render(request, 'payables/reports/vendor_balance.html', context)


@login_required
def expense_analysis(request):
    """Expense analysis report."""
    # Get parameters
    period = request.GET.get('period', 'monthly')
    year = int(request.GET.get('year', timezone.now().year))
    
    # Prepare data based on period
    if period == 'monthly':
        expense_data = []
        for month in range(1, 13):
            month_expenses = Expense.objects.filter(
                expense_date__year=year,
                expense_date__month=month
            )
            
            expense_data.append({
                'period': datetime(year, month, 1).strftime('%B'),
                'total': month_expenses.aggregate(total=Sum('total_amount'))['total'] or 0,
                'count': month_expenses.count()
            })
    
    elif period == 'quarterly':
        expense_data = []
        quarters = ['Q1', 'Q2', 'Q3', 'Q4']
        for i, quarter in enumerate(quarters):
            start_month = i * 3 + 1
            end_month = start_month + 2
            
            quarter_expenses = Expense.objects.filter(
                expense_date__year=year,
                expense_date__month__gte=start_month,
                expense_date__month__lte=end_month
            )
            
            expense_data.append({
                'period': quarter,
                'total': quarter_expenses.aggregate(total=Sum('total_amount'))['total'] or 0,
                'count': quarter_expenses.count()
            })
    
    # Category breakdown for the year
    category_breakdown = Expense.objects.filter(
        expense_date__year=year
    ).values('category__name').annotate(
        total=Sum('total_amount')
    ).order_by('-total')
    
    context = {
        'title': 'Expense Analysis',
        'expense_data': expense_data,
        'category_breakdown': category_breakdown,
        'period': period,
        'year': year,
        'years': range(timezone.now().year - 5, timezone.now().year + 1),
    }
    return render(request, 'payables/reports/expense_analysis.html', context)


@login_required
def bill_payment_history(request):
    """Bill payment history report."""
    # Get date range
    today = timezone.now().date()
    start_date = request.GET.get('start_date', today - timedelta(days=30))
    end_date = request.GET.get('end_date', today)
    
    # Get payments
    payments = Payment.objects.filter(
        payment_date__gte=start_date,
        payment_date__lte=end_date
    ).select_related('vendor').prefetch_related('allocations__bill')
    
    # Group by payment method
    payment_methods = payments.values('payment_method').annotate(
        count=Count('id'),
        total=Sum('amount')
    )
    
    context = {
        'title': 'Bill Payment History',
        'payments': payments,
        'payment_methods': payment_methods,
        'start_date': start_date,
        'end_date': end_date,
        'total_amount': payments.aggregate(total=Sum('amount'))['total'] or 0,
    }
    return render(request, 'payables/reports/bill_payment_history.html', context)


@login_required
def aging_summary(request):
    """Payables aging summary."""
    # Get all unpaid bills
    bills = Bill.objects.exclude(status__in=['paid', 'cancelled'])
    
    today = timezone.now().date()
    
    # Classify bills by age
    aging_buckets = {
        'current': [],
        '1_30': [],
        '31_60': [],
        '61_90': [],
        'over_90': []
    }
    
    for bill in bills:
        days_outstanding = (today - bill.due_date).days if bill.due_date < today else 0
        
        if days_outstanding <= 0:
            aging_buckets['current'].append(bill)
        elif days_outstanding <= 30:
            aging_buckets['1_30'].append(bill)
        elif days_outstanding <= 60:
            aging_buckets['31_60'].append(bill)
        elif days_outstanding <= 90:
            aging_buckets['61_90'].append(bill)
        else:
            aging_buckets['over_90'].append(bill)
    
    # Calculate totals
    totals = {
        'current': sum(bill.balance_due for bill in aging_buckets['current']),
        '1_30': sum(bill.balance_due for bill in aging_buckets['1_30']),
        '31_60': sum(bill.balance_due for bill in aging_buckets['31_60']),
        '61_90': sum(bill.balance_due for bill in aging_buckets['61_90']),
        'over_90': sum(bill.balance_due for bill in aging_buckets['over_90']),
    }
    totals['total'] = sum(totals.values())
    
    context = {
        'title': 'Payables Aging Summary',
        'aging_buckets': aging_buckets,
        'totals': totals,
        'today': today,
    }
    return render(request, 'payables/reports/aging_summary.html', context)


# AJAX endpoints
@login_required
def ajax_vendor_bills(request, vendor_id):
    """Get open bills for a vendor (AJAX)."""
    bills = Bill.objects.filter(
        vendor_id=vendor_id,
        status__in=['open', 'partially_paid', 'overdue']
    ).values('id', 'bill_number', 'balance_due')
    
    return JsonResponse(list(bills), safe=False)


@login_required
def ajax_bill_details(request, bill_id):
    """Get bill details (AJAX)."""
    bill = get_object_or_404(Bill, pk=bill_id)
    
    data = {
        'bill_number': bill.bill_number,
        'vendor': bill.vendor.company_name,
        'bill_date': bill.bill_date.isoformat(),
        'due_date': bill.due_date.isoformat(),
        'total': float(bill.total),
        'balance_due': float(bill.balance_due),
    }
    
    return JsonResponse(data)
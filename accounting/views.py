from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, Http404
from django.db import models, transaction
from django.db.models import Q, Sum, F
from django.core.exceptions import ValidationError
import csv
from .models import Account, Transaction, TransactionLine

@login_required
def home(request):
    # Calculate totals
    total_assets = Account.objects.filter(type='asset', status='active').aggregate(total=models.Sum('balance'))['total'] or 0
    total_liabilities = Account.objects.filter(type='liability', status='active').aggregate(total=models.Sum('balance'))['total'] or 0
    
    # Get month-to-date totals
    from datetime import datetime
    current_month = datetime.now().replace(day=1)
    revenue_mtd = Account.objects.filter(
        type='revenue',
        transactions__transaction__date__gte=current_month,
        transactions__credit__gt=0
    ).aggregate(total=models.Sum('transactions__credit'))['total'] or 0
    
    expenses_mtd = Account.objects.filter(
        type='expense',
        transactions__transaction__date__gte=current_month,
        transactions__debit__gt=0
    ).aggregate(total=models.Sum('transactions__debit'))['total'] or 0
    
    # Get recent transactions
    recent_transactions = Transaction.objects.all().order_by('-date', '-created_at')[:5]
    
    context = {
        'title': 'Accounting Dashboard',
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'revenue_mtd': revenue_mtd,
        'expenses_mtd': expenses_mtd,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'accounting/home.html', context)

@login_required
def chart_of_accounts(request):
    account_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')

    accounts = Account.objects.all()

    if account_type:
        accounts = accounts.filter(type=account_type)
    if status:
        accounts = accounts.filter(status=status)
    if search:
        accounts = accounts.filter(name__icontains=search) | accounts.filter(code__icontains=search)

    # Calculate totals for each account
    for account in accounts:
        account.total_debits = account.transactions.filter(debit__gt=0).aggregate(total=models.Sum('debit'))['total'] or 0
        account.total_credits = account.transactions.filter(credit__gt=0).aggregate(total=models.Sum('credit'))['total'] or 0

    accounts = accounts.order_by('code')
    paginator = Paginator(accounts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calculate overall totals
    all_accounts = Account.objects.all()
    total_opening_balance = all_accounts.aggregate(total=models.Sum('opening_balance'))['total'] or 0
    total_debits = TransactionLine.objects.filter(debit__gt=0).aggregate(total=models.Sum('debit'))['total'] or 0
    total_credits = TransactionLine.objects.filter(credit__gt=0).aggregate(total=models.Sum('credit'))['total'] or 0
    total_balance = all_accounts.aggregate(total=models.Sum('balance'))['total'] or 0

    context = {
        'title': 'Chart of Accounts',
        'accounts': page_obj,
        'all_accounts': Account.objects.filter(status='active'),
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
        'total_opening_balance': total_opening_balance,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'total_balance': total_balance,
    }
    return render(request, 'accounting/chart_of_accounts.html', context)

@login_required
def export_coa(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="chart_of_accounts.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Code', 'Name', 'Type', 'Parent', 'Description', 'Balance', 'Status'])
    
    accounts = Account.objects.all().order_by('code')
    for account in accounts:
        writer.writerow([
            account.code,
            account.name,
            account.get_type_display(),
            account.parent.name if account.parent else '-',
            account.description,
            account.balance,
            account.get_status_display()
        ])
    
    return response

@login_required
def account_create(request):
    if request.method == 'POST':
        try:
            account = Account(
                code=request.POST['code'],
                name=request.POST['name'],
                type=request.POST['type'],
                description=request.POST.get('description', ''),
                opening_balance=request.POST.get('opening_balance', 0),
                created_by=request.user
            )
            
            parent_id = request.POST.get('parent')
            if parent_id:
                account.parent = get_object_or_404(Account, id=parent_id)
            
            account.save()
            messages.success(request, 'Account created successfully.')
            return redirect('accounting:chart_of_accounts')
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return redirect('accounting:chart_of_accounts')

@login_required
def account_edit(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if request.method == 'POST':
        try:
            account.name = request.POST['name']
            account.description = request.POST.get('description', '')
            account.status = request.POST.get('status', account.status)
            account.save()
            messages.success(request, 'Account updated successfully.')
        except Exception as e:
            messages.error(request, f'Error updating account: {str(e)}')
    return redirect('accounting:chart_of_accounts')

@login_required
def account_delete(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if request.method == 'POST':
        try:
            if account.has_children:
                messages.error(request, 'Cannot delete account with child accounts.')
            elif account.balance != 0:
                messages.error(request, 'Cannot delete account with non-zero balance.')
            else:
                account.delete()
                messages.success(request, 'Account deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting account: {str(e)}')
    return redirect('accounting:chart_of_accounts')

@login_required
def account_detail(request, pk):
    account = get_object_or_404(Account, pk=pk)
    transactions = TransactionLine.objects.filter(account=account).order_by('-transaction__date')[:10]
    context = {
        'title': f'Account: {account.name}',
        'account': account,
        'recent_transactions': transactions,
    }
    return render(request, 'accounting/account_detail.html', context)

@login_required
def journal_entries(request):
    # Get filter parameters
    status = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    account_id = request.GET.get('account', '')

    # Base queryset
    transactions = Transaction.objects.filter(type='journal')

    # By default, show both draft and posted entries
    if not status:
        transactions = transactions.filter(Q(status='draft') | Q(status='posted'))
    else:
        transactions = transactions.filter(status=status)

    # Apply other filters
    if date_from:
        transactions = transactions.filter(date__gte=date_from)
    if date_to:
        transactions = transactions.filter(date__lte=date_to)
    if account_id:
        transactions = transactions.filter(lines__account_id=account_id).distinct()

    # Order by date and created_at
    transactions = transactions.order_by('-date', '-created_at')

    # Calculate totals for each transaction using annotate
    transactions = transactions.annotate(
        debit_total=models.Sum('lines__debit', filter=models.Q(lines__debit__gt=0)),
        credit_total=models.Sum('lines__credit', filter=models.Q(lines__credit__gt=0))
    )

    # Pagination
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'title': 'Journal Entries',
        'entries': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
        'accounts': Account.objects.filter(status='active').order_by('code'),
        'selected_status': status,
        'selected_account': account_id,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'accounting/journal_entries.html', context)

@login_required
def journal_entry_create(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get form data and validate totals
                accounts = request.POST.getlist('account[]')
                descriptions = request.POST.getlist('line_description[]')
                debits = [float(d or 0) for d in request.POST.getlist('debit[]')]
                credits = [float(c or 0) for c in request.POST.getlist('credit[]')]
                action = request.POST.get('action', 'save')

                # Validate totals before creating any records
                total_debit = sum(debits)
                total_credit = sum(credits)
                if abs(total_debit - total_credit) > 0.01:
                    raise ValidationError('Total debits must equal total credits.')

                # Create transaction with correct status
                transaction = Transaction.objects.create(
                    date=request.POST['date'],
                    type='journal',
                    reference=request.POST['reference'],
                    description=request.POST['description'],
                    status='posted' if action == 'post' else 'draft',
                    created_by=request.user
                )

                # Create transaction lines
                lines = []
                for i in range(len(accounts)):
                    if debits[i] > 0 or credits[i] > 0:
                        lines.append(TransactionLine(
                            transaction=transaction,
                            account_id=accounts[i],
                            description=descriptions[i],
                            debit=debits[i],
                            credit=credits[i]
                        ))
                TransactionLine.objects.bulk_create(lines)

                # Post the entry if requested
                if action == 'post':
                    transaction.status = 'posted'
                    transaction.save()
                    transaction.update_account_balances()
                    messages.success(request, 'Journal entry posted successfully.')
                else:
                    messages.success(request, 'Journal entry saved as draft.')


                return redirect('accounting:journal_entries')
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('accounting:journal_entry_create')
        except Exception as e:
            messages.error(request, f'Error creating journal entry: {str(e)}')
            return redirect('accounting:journal_entry_create')

    context = {
        'title': 'Create Journal Entry',
        'accounts': Account.objects.filter(status='active').order_by('code'),
    }
    return render(request, 'accounting/journal_entry.html', context)

@login_required
def journal_entry_detail(request, pk):
    # Get transaction with lines and account details
    transaction = get_object_or_404(Transaction.objects.select_related('created_by'), pk=pk, type='journal')
    
    # Get lines with their amounts and calculate totals
    lines = transaction.lines.select_related('account').all()
    total_debit = sum(line.debit or 0 for line in lines)
    total_credit = sum(line.credit or 0 for line in lines)
    
    context = {
        'title': f'Journal Entry: {transaction.reference}',
        'transaction': transaction,
        'lines': lines,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'accounts': Account.objects.filter(status='active').order_by('code'),
    }
    return render(request, 'accounting/journal_entry_detail.html', context)

@login_required
def journal_entry_edit(request, pk):
    # Get transaction with lines and account details
    entry = get_object_or_404(Transaction.objects.select_related('created_by'), pk=pk, type='journal')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                was_posted = entry.status == 'posted'
                action = request.POST.get('action', 'save')

                # If entry was posted, reverse the account balances
                if was_posted:
                    entry.update_account_balances(reverse=True)
                    entry.status = 'draft'
                    entry.save()

                # Update entry details
                entry.date = request.POST['date']
                entry.reference = request.POST['reference']
                entry.description = request.POST['description']
                entry.save()

                # Delete existing lines
                entry.lines.all().delete()

                # Create new lines
                accounts = request.POST.getlist('account[]')
                descriptions = request.POST.getlist('line_description[]')
                debits = request.POST.getlist('debit[]')
                credits = request.POST.getlist('credit[]')

                for i in range(len(accounts)):
                    if debits[i] or credits[i]:
                        TransactionLine.objects.create(
                            transaction=entry,
                            account_id=accounts[i],
                            description=descriptions[i],
                            debit=float(debits[i] or 0),
                            credit=float(credits[i] or 0)
                        )

                # Calculate and validate totals
                total_debit = sum(float(d or 0) for d in debits)
                total_credit = sum(float(c or 0) for c in credits)
                if abs(total_debit - total_credit) > 0.01:
                    raise ValidationError('Total debits must equal total credits.')

                # Handle posting
                if action == 'post' or was_posted:
                    entry.status = 'posted'
                    entry.save()
                    entry.update_account_balances()

            messages.success(request, f'Journal entry {"posted" if action == "post" else "updated"} successfully.')
            return redirect('accounting:journal_entry_detail', pk=pk)
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('accounting:journal_entry_edit', pk=pk)
        except Exception as e:
            messages.error(request, f'Error updating journal entry: {str(e)}')
            return redirect('accounting:journal_entry_edit', pk=pk)

    # Get lines with their amounts and calculate totals
    lines = entry.lines.select_related('account').all()
    total_debit = sum(line.debit or 0 for line in lines)
    total_credit = sum(line.credit or 0 for line in lines)
    
    context = {
        'title': 'Edit Journal Entry',
        'transaction': entry,
        'lines': lines,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'accounts': Account.objects.filter(status='active').order_by('code'),
        'is_edit': True
    }
    return render(request, 'accounting/journal_entry.html', context)

@login_required
def journal_entry_post(request, pk):
    if request.method == 'POST':
        # Get transaction with lines and account details
        entry = get_object_or_404(Transaction.objects.select_related('created_by'), pk=pk, type='journal')
        
        try:
            if entry.status != 'draft':
                messages.error(request, f'Journal entry is already {entry.status}.')
                return redirect('accounting:journal_entry_detail', pk=pk)

            # Get lines and calculate totals
            lines = entry.lines.select_related('account').all()
            total_debit = sum(line.debit or 0 for line in lines)
            total_credit = sum(line.credit or 0 for line in lines)

            # Verify debits equal credits
            if abs(total_debit - total_credit) > 0.01:  # Allow for small rounding differences
                messages.error(request, 'Total debits must equal total credits.')
                return redirect('accounting:journal_entry_detail', pk=pk)

            # Verify all lines have an account
            if entry.lines.filter(account__isnull=True).exists():
                messages.error(request, 'All lines must have an account selected.')
                return redirect('accounting:journal_entry_detail', pk=pk)

            with transaction.atomic():
                # Update account balances
                for line in entry.lines.select_related('account').all():
                    account = line.account
                    if line.debit:
                        if account.type in ['asset', 'expense']:
                            account.balance += line.debit
                        else:
                            account.balance -= line.debit
                    if line.credit:
                        if account.type in ['asset', 'expense']:
                            account.balance -= line.credit
                        else:
                            account.balance += line.credit
                    account.save()

                # Mark transaction as posted
                entry.status = 'posted'
                entry.save()
            
            messages.success(request, 'Journal entry posted successfully.')
        except Exception as e:
            messages.error(request, f'Error posting journal entry: {str(e)}')
    return redirect('accounting:journal_entry_detail', pk=pk)

@login_required
def journal_entry_delete(request, pk):
    if request.method == 'POST':
        entry = get_object_or_404(Transaction, pk=pk, type='journal')
        try:
            with transaction.atomic():
                # If entry was posted, reverse the account balances
                if entry.status == 'posted':
                    for line in entry.lines.select_related('account').all():
                        account = line.account
                        if line.debit:
                            if account.type in ['asset', 'expense']:
                                account.balance -= line.debit
                            else:
                                account.balance += line.debit
                        if line.credit:
                            if account.type in ['asset', 'expense']:
                                account.balance += line.credit
                            else:
                                account.balance -= line.credit
                        account.save()

                entry.delete()
                messages.success(request, 'Journal entry deleted successfully.')
                return redirect('accounting:journal_entries')
        except Exception as e:
            messages.error(request, f'Error deleting journal entry: {str(e)}')
    return redirect('accounting:journal_entry_detail', pk=pk)
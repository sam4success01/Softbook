# payables/forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import (
    Vendor, Bill, BillItem, Expense, Payment, PaymentAllocation,
    PurchaseOrder, PurchaseOrderItem, ExpenseCategory, RecurringBill
)


class VendorForm(forms.ModelForm):
    """Form for creating and updating vendors."""
    
    class Meta:
        model = Vendor
        fields = [
            'vendor_type', 'company_name', 'contact_person', 'email', 'phone', 'website',
            'billing_address_line1', 'billing_address_line2', 'billing_city', 
            'billing_state', 'billing_postal_code', 'billing_country',
            'tax_number', 'payment_terms', 'custom_payment_terms', 'credit_limit',
            'opening_balance', 'bank_name', 'bank_account_number', 'bank_routing_number',
            'bank_swift_code', 'notes', 'is_active'
        ]
        widgets = {
            'vendor_type': forms.Select(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'billing_address_line1': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_address_line2': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_city': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_state': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'billing_country': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_number': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_terms': forms.Select(attrs={'class': 'form-control'}),
            'custom_payment_terms': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_routing_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_swift_code': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show/hide custom_payment_terms based on payment_terms selection
        self.fields['custom_payment_terms'].widget.attrs['style'] = 'display:none;'


class BillForm(forms.ModelForm):
    """Form for creating and updating bills."""
    
    class Meta:
        model = Bill
        fields = [
            'vendor', 'vendor_bill_number', 'bill_date', 'due_date', 
            'status', 'discount_amount', 'notes', 'attachment'
        ]
        widgets = {
            'vendor': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'vendor_bill_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bill_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }


class BillItemForm(forms.ModelForm):
    """Form for bill line items."""
    
    class Meta:
        model = BillItem
        fields = ['expense_category', 'description', 'quantity', 'unit_price', 'tax_rate']
        widgets = {
            'expense_category': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': '0.01', 'data-calc': 'true'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'data-calc': 'true'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'data-calc': 'true'}),
        }


# Inline formset for bill items
BillItemFormSet = inlineformset_factory(
    Bill, BillItem,
    form=BillItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class ExpenseForm(forms.ModelForm):
    """Form for recording expenses."""
    
    class Meta:
        model = Expense
        fields = [
            'vendor', 'expense_date', 'category', 'amount', 'tax_amount',
            'payment_mode', 'reference_number', 'description', 'is_billable',
            'customer', 'status', 'receipt', 'notes'
        ]
        widgets = {
            'vendor': forms.Select(attrs={'class': 'form-control'}),
            'expense_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'category': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': '0.01', 'required': True}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'payment_mode': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': True}),
            'is_billable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show customer field if is_billable is checked
        self.fields['customer'].required = False
        # Import Customer model here to avoid circular imports
        from invoicing.models import Customer
        self.fields['customer'].queryset = Customer.objects.all()


class PaymentForm(forms.ModelForm):
    """Form for vendor payments."""
    
    class Meta:
        model = Payment
        fields = [
            'vendor', 'payment_date', 'amount', 'payment_method',
            'reference_number', 'bank_charges', 'notes'
        ]
        widgets = {
            'vendor': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': '0.01', 'required': True}),
            'payment_method': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_charges': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PaymentAllocationForm(forms.ModelForm):
    """Form for allocating payments to bills."""
    
    class Meta:
        model = PaymentAllocation
        fields = ['bill', 'amount']
        widgets = {
            'bill': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show open bills
        if 'instance' in kwargs and kwargs['instance']:
            vendor = kwargs['instance'].payment.vendor
            self.fields['bill'].queryset = Bill.objects.filter(
                vendor=vendor,
                status__in=['open', 'partially_paid', 'overdue']
            )


# Inline formset for payment allocations
PaymentAllocationFormSet = inlineformset_factory(
    Payment, PaymentAllocation,
    form=PaymentAllocationForm,
    extra=1,
    can_delete=True
)


class PurchaseOrderForm(forms.ModelForm):
    """Form for creating purchase orders."""
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'vendor', 'po_date', 'expected_delivery_date', 'status',
            'ship_to_address', 'discount_amount', 'terms_and_conditions', 'notes'
        ]
        widgets = {
            'vendor': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'po_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'expected_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'ship_to_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'terms_and_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PurchaseOrderItemForm(forms.ModelForm):
    """Form for purchase order line items."""
    
    class Meta:
        model = PurchaseOrderItem
        fields = ['item_name', 'description', 'quantity', 'unit_price', 'tax_rate']
        widgets = {
            'item_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': '0.01', 'data-calc': 'true'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'data-calc': 'true'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'data-calc': 'true'}),
        }


# Inline formset for purchase order items
PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder, PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class ExpenseCategoryForm(forms.ModelForm):
    """Form for expense categories."""
    
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'code', 'description', 'parent', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prevent selecting itself as parent
        if self.instance.pk:
            self.fields['parent'].queryset = ExpenseCategory.objects.exclude(pk=self.instance.pk)


class RecurringBillForm(forms.ModelForm):
    """Form for recurring bills."""
    
    class Meta:
        model = RecurringBill
        fields = [
            'name', 'vendor', 'frequency', 'start_date', 'end_date',
            'category', 'amount', 'tax_rate', 'description', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'vendor': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'frequency': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'category': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'required': True}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': True}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BillFilterForm(forms.Form):
    """Form for filtering bills."""
    vendor = forms.ModelChoiceField(
        queryset=Vendor.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="All Vendors"
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Bill.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'placeholder': 'From Date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'placeholder': 'To Date'})
    )
    min_amount = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'placeholder': 'Min Amount'})
    )
    max_amount = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'placeholder': 'Max Amount'})
    )


class ExpenseFilterForm(forms.Form):
    """Form for filtering expenses."""
    vendor = forms.ModelChoiceField(
        queryset=Vendor.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="All Vendors"
    )
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="All Categories"
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Expense.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'placeholder': 'From Date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'placeholder': 'To Date'})
    )
    is_billable = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Billable'), ('false', 'Non-billable')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


# Additional utility forms

class BulkPaymentForm(forms.Form):
    """Form for bulk payment processing."""
    vendor = forms.ModelChoiceField(
        queryset=Vendor.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        label="Select Vendor"
    )
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
        label="Payment Date"
    )
    payment_method = forms.ChoiceField(
        choices=Payment.PAYMENT_METHODS,
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        label="Payment Method"
    )
    bills = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label="Select Bills to Pay"
    )
    
    def __init__(self, *args, **kwargs):
        vendor_id = kwargs.pop('vendor_id', None)
        super().__init__(*args, **kwargs)
        
        if vendor_id:
            vendor = Vendor.objects.get(pk=vendor_id)
            self.fields['vendor'].initial = vendor
            bills = Bill.objects.filter(
                vendor=vendor,
                status__in=['open', 'partially_paid', 'overdue']
            )
            self.fields['bills'].choices = [
                (bill.id, f"{bill.bill_number} - ${bill.balance_due}")
                for bill in bills
            ]


class QuickExpenseForm(forms.ModelForm):
    """Simplified form for quick expense entry."""
    
    class Meta:
        model = Expense
        fields = ['category', 'amount', 'description', 'expense_date', 'payment_mode']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': '0.01', 'required': True}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'expense_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'payment_mode': forms.Select(attrs={'class': 'form-control', 'required': True}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expense_date'].initial = timezone.now().date()
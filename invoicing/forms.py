from django import forms
from django.utils import timezone
from django.forms import inlineformset_factory
from .models import Customer, Item, InvoiceTemplate, Invoice, InvoiceItem, Payment, Settings


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'customer_type', 'company_name', 'first_name', 'last_name', 
            'email', 'phone', 'address_line1', 'address_line2', 
            'city', 'state', 'postal_code', 'country', 
            'tax_number', 'notes'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make company name required only for business customers
        self.fields['company_name'].required = False
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            'name', 'description', 'item_type', 'unit_price', 
            'tax_rate', 'is_active', 'sku'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if field_name == 'is_active':
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'


class InvoiceTemplateForm(forms.ModelForm):
    class Meta:
        model = InvoiceTemplate
        fields = [
            'name', 'header', 'footer', 'terms', 'notes', 
            'logo', 'primary_color', 'is_default'
        ]
        widgets = {
            'header': forms.Textarea(attrs={'rows': 3}),
            'footer': forms.Textarea(attrs={'rows': 3}),
            'terms': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'primary_color': forms.TextInput(attrs={'type': 'color'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if field_name == 'is_default':
                field.widget.attrs['class'] = 'form-check-input'
            elif field_name == 'logo':
                field.widget.attrs['class'] = 'form-control-file'
            else:
                field.widget.attrs['class'] = 'form-control'


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'invoice_number', 'customer', 'issue_date', 'due_date',
            'template', 'status', 'notes', 'terms', 'discount_amount'
        ]
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'terms': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # Make invoice number optional for new invoices
        self.fields['invoice_number'].required = False
        
        # Set current date as default for issue_date if not provided
        if not self.initial.get('issue_date'):
            self.initial['issue_date'] = timezone.now().date()


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['item', 'description', 'quantity', 'unit_price', 'tax_rate']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # Make item field optional
        self.fields['item'].required = False
        
        # Add data attributes for dynamic calculations
        self.fields['quantity'].widget.attrs['data-calc'] = 'true'
        self.fields['unit_price'].widget.attrs['data-calc'] = 'true'
        self.fields['tax_rate'].widget.attrs['data-calc'] = 'true'


# Create the formset for invoice items
InvoiceItemFormSet = inlineformset_factory(
    Invoice, InvoiceItem, form=InvoiceItemForm,
    extra=1, can_delete=True
)


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_date', 'payment_method', 'reference_number', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # Set current date as default for payment_date if not provided
        if not self.initial.get('payment_date'):
            self.initial['payment_date'] = timezone.now().date()


class SettingsForm(forms.ModelForm):
    class Meta:
        model = Settings
        fields = [
            'company_name', 'company_address', 'company_phone', 
            'company_email', 'company_website', 'company_tax_number',
            'default_payment_terms', 'default_tax_rate', 
            'invoice_note_default', 'invoice_terms_default',
            'invoice_prefix', 'next_invoice_number',
            'default_template', 'currency', 'logo'
        ]
        widgets = {
            'company_address': forms.Textarea(attrs={'rows': 3}),
            'invoice_note_default': forms.Textarea(attrs={'rows': 3}),
            'invoice_terms_default': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if field_name == 'logo':
                field.widget.attrs['class'] = 'form-control-file'
            else:
                field.widget.attrs['class'] = 'form-control'


class InvoiceFilterForm(forms.Form):
    """Form for filtering invoices on the list view."""
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Invoice.STATUS_CHOICES,
        required=False
    )
    
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        required=False
    )
    
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    
    min_amount = forms.DecimalField(
        required=False,
        min_value=0
    )
    
    max_amount = forms.DecimalField(
        required=False,
        min_value=0
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
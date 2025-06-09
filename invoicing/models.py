from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.urls import reverse
import uuid


class Customer(models.Model):
    """Customer model for invoicing."""
    CUSTOMER_TYPES = [
        ('business', 'Business'),
        ('individual', 'Individual'),
    ]
    
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default='business')
    company_name = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    tax_number = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='customers_created')
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        if self.customer_type == 'business' and self.company_name:
            return self.company_name
        return f"{self.first_name} {self.last_name}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_full_address(self):
        address_parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ", ".join([part for part in address_parts if part])
    
    def get_absolute_url(self):
        return reverse('invoicing:customer_detail', args=[self.pk])


class Item(models.Model):
    """Items/Services that can be included in invoices."""
    ITEM_TYPES = [
        ('product', 'Product'),
        ('service', 'Service'),
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default='service')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    sku = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='items_created')
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name


class InvoiceTemplate(models.Model):
    """Template for invoices."""
    name = models.CharField(max_length=100)
    header = models.TextField(blank=True, null=True)
    footer = models.TextField(blank=True, null=True)
    terms = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='invoice_logos/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#007bff')  # Hex color code
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='invoice_templates_created')
    
    class Meta:
        ordering = ['-is_default', 'name']
        
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.is_default:
            # Set all other templates to not be default
            InvoiceTemplate.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Invoice(models.Model):
    """Invoice model."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('viewed', 'Viewed'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices')
    issue_date = models.DateField()
    due_date = models.DateField()
    template = models.ForeignKey(InvoiceTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True, null=True)
    terms = models.TextField(blank=True, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pdf_file = models.FileField(upload_to='invoices/', blank=True, null=True)
    public_url = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='invoices_created')
    
    class Meta:
        ordering = ['-issue_date', '-created_at']
        
    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.customer}"
    
    def save(self, *args, **kwargs):
        # Auto-generate invoice number if not provided
        if not self.invoice_number:
            last_invoice = Invoice.objects.order_by('-id').first()
            last_id = last_invoice.id if last_invoice else 0
            self.invoice_number = f"INV-{(last_id + 1):06d}"
        
        # Only calculate totals if this invoice already exists (has an ID)
        if self.pk:
            # Calculate totals
            self.subtotal = sum(item.line_total for item in self.items.all())
            self.tax_amount = sum(item.tax_amount for item in self.items.all())
            self.total = self.subtotal + self.tax_amount - (self.discount_amount or 0)
            self.balance_due = self.total - (self.amount_paid or 0)
            
            # Update status based on payments
            today = timezone.now().date()
            if self.status not in ['cancelled', 'draft']:
                if self.balance_due <= 0:
                    self.status = 'paid'
                elif self.amount_paid > 0 and self.balance_due > 0:
                    self.status = 'partially_paid'
                elif self.due_date < today:
                    self.status = 'overdue'
        else:
            # For new invoices, set initial totals
            if not self.subtotal:
                self.subtotal = 0
            if not self.tax_amount:
                self.tax_amount = 0
            if not self.total:
                self.total = self.subtotal + self.tax_amount - (self.discount_amount or 0)
            if not self.balance_due:
                self.balance_due = self.total - (self.amount_paid or 0)
        
        super().save(*args, **kwargs)
        
    def get_absolute_url(self):
        return reverse('invoicing:invoice_detail', args=[self.pk])
    
    def get_public_url(self):
        return reverse('invoicing:invoice_public', args=[self.public_url])
    
    def get_line_items_count(self):
        return self.items.count()
    
    @property
    def is_paid(self):
        return self.status == 'paid'
    
    @property
    def is_overdue(self):
        return self.status == 'overdue'
    
    @property
    def days_overdue(self):
        if self.due_date < timezone.now().date():
            return (timezone.now().date() - self.due_date).days
        return 0


class InvoiceItem(models.Model):
    """Line items for invoices."""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.description} ({self.quantity} x ${self.unit_price})"
    
    def save(self, *args, **kwargs):
        # Calculate line total and tax amount
        self.line_total = self.quantity * self.unit_price
        self.tax_amount = self.line_total * (self.tax_rate / 100)
        
        # Save the item first
        super().save(*args, **kwargs)
        
        # Then update the invoice totals
        self.invoice.save()


class Payment(models.Model):
    """Payments made against invoices."""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
        ('other', 'Other'),
    ]
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='payments_created')
    
    class Meta:
        ordering = ['-payment_date', '-created_at']
    
    def __str__(self):
        return f"Payment of ${self.amount} for {self.invoice}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update invoice after payment is saved
        self.invoice.amount_paid = self.invoice.payments.aggregate(total=models.Sum('amount'))['total'] or 0
        self.invoice.save()


class Settings(models.Model):
    """Global invoicing settings."""
    company_name = models.CharField(max_length=255)
    company_address = models.TextField()
    company_phone = models.CharField(max_length=20, blank=True, null=True)
    company_email = models.EmailField(blank=True, null=True)
    company_website = models.URLField(blank=True, null=True)
    company_tax_number = models.CharField(max_length=50, blank=True, null=True)
    default_payment_terms = models.IntegerField(default=30, help_text="Default number of days until payment is due")
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    invoice_note_default = models.TextField(blank=True, null=True)
    invoice_terms_default = models.TextField(blank=True, null=True)
    invoice_prefix = models.CharField(max_length=10, default="INV-")
    next_invoice_number = models.IntegerField(default=1)
    default_template = models.ForeignKey(InvoiceTemplate, on_delete=models.SET_NULL, blank=True, null=True)
    currency = models.CharField(max_length=3, default="USD")
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Settings"
    
    def __str__(self):
        return f"Invoice Settings for {self.company_name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one settings instance exists
        if not self.pk and Settings.objects.exists():
            # Update existing instance instead of creating a new one
            self.pk = Settings.objects.first().pk
        super().save(*args, **kwargs)

# Add this method to your Invoice model class:

def calculate_totals(self):
    """Recalculate all totals for this invoice."""
    if self.pk:  # Only if invoice exists
        # Calculate subtotal and tax from line items
        self.subtotal = sum(item.line_total for item in self.items.all())
        self.tax_amount = sum(item.tax_amount for item in self.items.all())
        
        # Calculate total
        self.total = self.subtotal + self.tax_amount - (self.discount_amount or 0)
        
        # Calculate balance due
        total_paid = self.payments.aggregate(total=models.Sum('amount'))['total'] or 0
        self.amount_paid = total_paid
        self.balance_due = self.total - self.amount_paid
        
        # Update status
        today = timezone.now().date()
        if self.status not in ['cancelled', 'draft']:
            if self.balance_due <= 0:
                self.status = 'paid'
            elif self.amount_paid > 0 and self.balance_due > 0:
                self.status = 'partially_paid'
            elif self.due_date < today:
                self.status = 'overdue'
        
        # Note: Don't call save() here - let the caller decide when to save
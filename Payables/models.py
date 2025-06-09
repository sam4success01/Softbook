# payables/models.py

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.urls import reverse
import uuid


class Vendor(models.Model):
    """Vendor/Supplier model for payables."""
    VENDOR_TYPES = [
        ('company', 'Company'),
        ('individual', 'Individual'),
    ]
    
    PAYMENT_TERMS = [
        ('net15', 'Net 15'),
        ('net30', 'Net 30'),
        ('net45', 'Net 45'),
        ('net60', 'Net 60'),
        ('due_on_receipt', 'Due on Receipt'),
        ('custom', 'Custom'),
    ]
    
    vendor_type = models.CharField(max_length=20, choices=VENDOR_TYPES, default='company')
    company_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    # Address fields
    billing_address_line1 = models.CharField(max_length=255, blank=True, null=True)
    billing_address_line2 = models.CharField(max_length=255, blank=True, null=True)
    billing_city = models.CharField(max_length=100, blank=True, null=True)
    billing_state = models.CharField(max_length=100, blank=True, null=True)
    billing_postal_code = models.CharField(max_length=20, blank=True, null=True)
    billing_country = models.CharField(max_length=100, blank=True, null=True)
    
    # Financial details
    tax_number = models.CharField(max_length=50, blank=True, null=True)
    payment_terms = models.CharField(max_length=20, choices=PAYMENT_TERMS, default='net30')
    custom_payment_terms = models.IntegerField(blank=True, null=True, help_text="Days until payment is due")
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    opening_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Bank details
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account_number = models.CharField(max_length=50, blank=True, null=True)
    bank_routing_number = models.CharField(max_length=50, blank=True, null=True)
    bank_swift_code = models.CharField(max_length=20, blank=True, null=True)
    
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='vendors_created')
    
    class Meta:
        ordering = ['company_name']
        
    def __str__(self):
        return self.company_name
    
    def get_absolute_url(self):
        return reverse('payables:vendor_detail', args=[self.pk])
    
    def get_payment_terms_days(self):
        """Get payment terms in days."""
        if self.payment_terms == 'custom':
            return self.custom_payment_terms or 30
        elif self.payment_terms == 'due_on_receipt':
            return 0
        else:
            # Extract number from 'net15', 'net30', etc.
            return int(self.payment_terms.replace('net', ''))
    
    def get_outstanding_amount(self):
        """Get total outstanding amount for this vendor."""
        from django.db.models import Sum
        outstanding = self.bills.filter(
            status__in=['draft', 'open', 'partially_paid', 'overdue']
        ).aggregate(total=Sum('balance_due'))['total'] or 0
        return outstanding


class ExpenseCategory(models.Model):
    """Categories for expenses and bills."""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['code']
        verbose_name_plural = 'Expense Categories'
        
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} - {self.name}"
        return self.name


class Bill(models.Model):
    """Bills from vendors."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    bill_number = models.CharField(max_length=50, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='bills')
    vendor_bill_number = models.CharField(max_length=50, blank=True, null=True, help_text="Vendor's bill/invoice number")
    bill_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Financial fields
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True, null=True)
    attachment = models.FileField(upload_to='bill_attachments/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='bills_created')
    
    class Meta:
        ordering = ['-bill_date', '-created_at']
        
    def __str__(self):
        return f"Bill #{self.bill_number} - {self.vendor}"
    
    def save(self, *args, **kwargs):
        # Auto-generate bill number if not provided
        if not self.bill_number:
            last_bill = Bill.objects.order_by('-id').first()
            last_id = last_bill.id if last_bill else 0
            self.bill_number = f"BILL-{(last_id + 1):06d}"
        
        # Calculate totals only if bill exists
        if self.pk:
            self.subtotal = sum(item.line_total for item in self.items.all())
            self.tax_amount = sum(item.tax_amount for item in self.items.all())
            self.total = self.subtotal + self.tax_amount - (self.discount_amount or 0)
            self.balance_due = self.total - (self.amount_paid or 0)
            
            # Update status
            today = timezone.now().date()
            if self.status not in ['cancelled', 'draft']:
                if self.balance_due <= 0:
                    self.status = 'paid'
                elif self.amount_paid > 0 and self.balance_due > 0:
                    self.status = 'partially_paid'
                elif self.due_date < today:
                    self.status = 'overdue'
        else:
            # For new bills, set initial totals
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
        return reverse('payables:bill_detail', args=[self.pk])
    
    def calculate_totals(self):
        """Recalculate all totals for this bill."""
        if self.pk:
            self.subtotal = sum(item.line_total for item in self.items.all())
            self.tax_amount = sum(item.tax_amount for item in self.items.all())
            self.total = self.subtotal + self.tax_amount - (self.discount_amount or 0)
            
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


class BillItem(models.Model):
    """Line items for bills."""
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    expense_category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    description = models.TextField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1, validators=[MinValueValidator(0.01)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.description} ({self.quantity} x ${self.unit_price})"
    
    def save(self, *args, **kwargs):
        # Calculate line total and tax
        self.line_total = self.quantity * self.unit_price
        self.tax_amount = self.line_total * (self.tax_rate / 100)
        
        super().save(*args, **kwargs)
        
        # Update bill totals
        if self.bill_id:
            self.bill.save()


class Expense(models.Model):
    """Direct expenses (not from bills)."""
    PAYMENT_MODES = [
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('recorded', 'Recorded'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('reimbursed', 'Reimbursed'),
    ]
    
    expense_number = models.CharField(max_length=50, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, null=True, blank=True, related_name='expenses')
    expense_date = models.DateField()
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    is_billable = models.BooleanField(default=False)
    customer = models.ForeignKey('invoicing.Customer', on_delete=models.SET_NULL, null=True, blank=True, help_text="If billable to customer")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='recorded')
    receipt = models.FileField(upload_to='expense_receipts/', blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='expenses_created')
    
    class Meta:
        ordering = ['-expense_date', '-created_at']
        
    def __str__(self):
        return f"Expense #{self.expense_number} - {self.category}"
    
    def save(self, *args, **kwargs):
        # Auto-generate expense number
        if not self.expense_number:
            last_expense = Expense.objects.order_by('-id').first()
            last_id = last_expense.id if last_expense else 0
            self.expense_number = f"EXP-{(last_id + 1):06d}"
        
        # Calculate total
        self.total_amount = self.amount + self.tax_amount
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('payables:expense_detail', args=[self.pk])


class Payment(models.Model):
    """Payments made to vendors."""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('other', 'Other'),
    ]
    
    payment_number = models.CharField(max_length=50, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='payments')
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Bank details
    bank_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='vendor_payments_created')
    
    class Meta:
        ordering = ['-payment_date', '-created_at']
        
    def __str__(self):
        return f"Payment #{self.payment_number} - ${self.amount} to {self.vendor}"
    
    def save(self, *args, **kwargs):
        # Auto-generate payment number
        if not self.payment_number:
            last_payment = Payment.objects.order_by('-id').first()
            last_id = last_payment.id if last_payment else 0
            self.payment_number = f"PAY-{(last_id + 1):06d}"
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('payables:payment_detail', args=[self.pk])


class PaymentAllocation(models.Model):
    """Allocation of payments to specific bills."""
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='allocations')
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payment_allocations')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    
    class Meta:
        unique_together = ['payment', 'bill']
        
    def __str__(self):
        return f"${self.amount} from Payment #{self.payment.payment_number} to Bill #{self.bill.bill_number}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update bill's paid amount
        self.bill.amount_paid = self.bill.payment_allocations.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        self.bill.save()


class PurchaseOrder(models.Model):
    """Purchase orders to vendors."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('billed', 'Billed'),
        ('cancelled', 'Cancelled'),
    ]
    
    po_number = models.CharField(max_length=50, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='purchase_orders')
    po_date = models.DateField()
    expected_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Delivery details
    ship_to_address = models.TextField(blank=True, null=True)
    
    # Financial fields
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    terms_and_conditions = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='purchase_orders_created')
    
    class Meta:
        ordering = ['-po_date', '-created_at']
        
    def __str__(self):
        return f"PO #{self.po_number} - {self.vendor}"
    
    def save(self, *args, **kwargs):
        # Auto-generate PO number
        if not self.po_number:
            last_po = PurchaseOrder.objects.order_by('-id').first()
            last_id = last_po.id if last_po else 0
            self.po_number = f"PO-{(last_id + 1):06d}"
        
        # Calculate totals only if PO exists
        if self.pk:
            self.subtotal = sum(item.line_total for item in self.items.all())
            self.tax_amount = sum(item.tax_amount for item in self.items.all())
            self.total = self.subtotal + self.tax_amount - (self.discount_amount or 0)
        else:
            # For new POs
            if not self.subtotal:
                self.subtotal = 0
            if not self.tax_amount:
                self.tax_amount = 0
            if not self.total:
                self.total = self.subtotal + self.tax_amount - (self.discount_amount or 0)
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('payables:po_detail', args=[self.pk])


class PurchaseOrderItem(models.Model):
    """Line items for purchase orders."""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.item_name} ({self.quantity} x ${self.unit_price})"
    
    def save(self, *args, **kwargs):
        # Calculate line total and tax
        self.line_total = self.quantity * self.unit_price
        self.tax_amount = self.line_total * (self.tax_rate / 100)
        
        super().save(*args, **kwargs)
        
        # Update PO totals
        if self.purchase_order_id:
            self.purchase_order.save()


class RecurringBill(models.Model):
    """Template for recurring bills."""
    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    
    name = models.CharField(max_length=200)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='recurring_bills')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_bill_date = models.DateField()
    
    # Template fields
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    description = models.TextField()
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    
    class Meta:
        ordering = ['next_bill_date']
        
    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"
    
    def create_bill(self):
        """Create a bill from this recurring template."""
        from datetime import timedelta
        
        bill = Bill.objects.create(
            vendor=self.vendor,
            bill_date=self.next_bill_date,
            due_date=self.next_bill_date + timedelta(days=self.vendor.get_payment_terms_days()),
            notes=f"Generated from recurring bill: {self.name}",
            created_by=self.created_by
        )
        
        # Create bill item
        BillItem.objects.create(
            bill=bill,
            expense_category=self.category,
            description=self.description,
            quantity=1,
            unit_price=self.amount,
            tax_rate=self.tax_rate
        )
        
        # Update next bill date
        if self.frequency == 'weekly':
            self.next_bill_date += timedelta(weeks=1)
        elif self.frequency == 'monthly':
            # Add one month
            if self.next_bill_date.month == 12:
                self.next_bill_date = self.next_bill_date.replace(year=self.next_bill_date.year + 1, month=1)
            else:
                self.next_bill_date = self.next_bill_date.replace(month=self.next_bill_date.month + 1)
        elif self.frequency == 'quarterly':
            # Add 3 months
            for _ in range(3):
                if self.next_bill_date.month == 12:
                    self.next_bill_date = self.next_bill_date.replace(year=self.next_bill_date.year + 1, month=1)
                else:
                    self.next_bill_date = self.next_bill_date.replace(month=self.next_bill_date.month + 1)
        elif self.frequency == 'yearly':
            self.next_bill_date = self.next_bill_date.replace(year=self.next_bill_date.year + 1)
        
        # Check if we should deactivate
        if self.end_date and self.next_bill_date > self.end_date:
            self.is_active = False
        
        self.save()
        
        return bill
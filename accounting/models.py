from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.PROTECT)
    description = models.TextField(blank=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='accounts_created')
    level = models.IntegerField(default=0)  # For hierarchical display

    class Meta:
        ordering = ['code']
        unique_together = ['parent', 'code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        if self.parent:
            if self.parent == self:
                raise ValidationError(_('An account cannot be its own parent.'))
            if self.type != self.parent.type:
                raise ValidationError(_('Child account must be of the same type as parent.'))
            self.level = self.parent.level + 1
        else:
            self.level = 0

    def save(self, *args, **kwargs):
        self.clean()
        if self._state.adding:  # Only on creation
            self.balance = self.opening_balance
        super().save(*args, **kwargs)

    @property
    def has_children(self):
        return self.children.exists()

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('journal', 'Journal Entry'),
        ('invoice', 'Invoice'),
        ('bill', 'Bill'),
        ('payment', 'Payment'),
        ('receipt', 'Receipt'),
    ]

    date = models.DateField()
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    reference = models.CharField(max_length=50)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('voided', 'Voided'),
    ]
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')

    class Meta:
        ordering = ['-date', '-created_at']

    @property
    def total_debit(self):
        return sum(line.debit for line in self.lines.all())

    @property
    def total_credit(self):
        return sum(line.credit for line in self.lines.all())

    def clean(self):
        if self.lines.exists():
            total_debit = self.total_debit
            total_credit = self.total_credit
            if total_debit != total_credit:
                raise ValidationError(_('Total debits must equal total credits.'))

    def update_account_balances(self, reverse=False):
        multiplier = -1 if reverse else 1
        for line in self.lines.all():
            if line.debit:
                if line.account.type in ['asset', 'expense']:
                    line.account.balance += (line.debit * multiplier)
                else:
                    line.account.balance -= (line.debit * multiplier)
            if line.credit:
                if line.account.type in ['asset', 'expense']:
                    line.account.balance -= (line.credit * multiplier)
                else:
                    line.account.balance += (line.credit * multiplier)
            line.account.save()

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        old_status = None if is_new else Transaction.objects.get(pk=self.pk).status
        
        if not is_new and old_status != self.status:
            if old_status == 'posted' and self.status == 'draft':
                self.update_account_balances(reverse=True)
            elif old_status == 'draft' and self.status == 'posted':
                self.clean()  # Validate debits = credits
                self.update_account_balances()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_type_display()} - {self.reference}"

class TransactionLine(models.Model):
    transaction = models.ForeignKey(Transaction, related_name='lines', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, related_name='transactions', on_delete=models.PROTECT)
    description = models.CharField(max_length=255)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.account.code} - {self.description}"

    def clean(self):
        # Convert to float and handle None values
        debit = float(self.debit or 0)
        credit = float(self.credit or 0)

        if debit < 0 or credit < 0:
            raise ValidationError(_('Amounts cannot be negative.'))
        if debit > 0 and credit > 0:
            raise ValidationError(_('A line cannot have both debit and credit amounts.'))
        if debit == 0 and credit == 0:
            raise ValidationError(_('A line must have either a debit or credit amount.'))

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
# Generated by Django 5.1.7 on 2025-06-08 01:00

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('invoicing', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Bill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bill_number', models.CharField(max_length=50, unique=True)),
                ('vendor_bill_number', models.CharField(blank=True, help_text="Vendor's bill/invoice number", max_length=50, null=True)),
                ('bill_date', models.DateField()),
                ('due_date', models.DateField()),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('open', 'Open'), ('partially_paid', 'Partially Paid'), ('paid', 'Paid'), ('overdue', 'Overdue'), ('cancelled', 'Cancelled')], default='draft', max_length=20)),
                ('subtotal', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('tax_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('amount_paid', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('balance_due', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('notes', models.TextField(blank=True, null=True)),
                ('attachment', models.FileField(blank=True, null=True, upload_to='bill_attachments/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bills_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-bill_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ExpenseCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=20, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='subcategories', to='Payables.expensecategory')),
            ],
            options={
                'verbose_name_plural': 'Expense Categories',
                'ordering': ['code'],
            },
        ),
        migrations.CreateModel(
            name='BillItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField()),
                ('quantity', models.DecimalField(decimal_places=2, default=1, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)])),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('tax_rate', models.DecimalField(decimal_places=2, default=0, max_digits=5, validators=[django.core.validators.MinValueValidator(0)])),
                ('line_total', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('tax_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('bill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='Payables.bill')),
                ('expense_category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='Payables.expensecategory')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='PurchaseOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('po_number', models.CharField(max_length=50, unique=True)),
                ('po_date', models.DateField()),
                ('expected_delivery_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('sent', 'Sent'), ('accepted', 'Accepted'), ('billed', 'Billed'), ('cancelled', 'Cancelled')], default='draft', max_length=20)),
                ('ship_to_address', models.TextField(blank=True, null=True)),
                ('subtotal', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('tax_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('terms_and_conditions', models.TextField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='purchase_orders_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-po_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PurchaseOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)])),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('tax_rate', models.DecimalField(decimal_places=2, default=0, max_digits=5, validators=[django.core.validators.MinValueValidator(0)])),
                ('line_total', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('tax_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('purchase_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='Payables.purchaseorder')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='Vendor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vendor_type', models.CharField(choices=[('company', 'Company'), ('individual', 'Individual')], default='company', max_length=20)),
                ('company_name', models.CharField(max_length=255)),
                ('contact_person', models.CharField(blank=True, max_length=200, null=True)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('website', models.URLField(blank=True, null=True)),
                ('billing_address_line1', models.CharField(blank=True, max_length=255, null=True)),
                ('billing_address_line2', models.CharField(blank=True, max_length=255, null=True)),
                ('billing_city', models.CharField(blank=True, max_length=100, null=True)),
                ('billing_state', models.CharField(blank=True, max_length=100, null=True)),
                ('billing_postal_code', models.CharField(blank=True, max_length=20, null=True)),
                ('billing_country', models.CharField(blank=True, max_length=100, null=True)),
                ('tax_number', models.CharField(blank=True, max_length=50, null=True)),
                ('payment_terms', models.CharField(choices=[('net15', 'Net 15'), ('net30', 'Net 30'), ('net45', 'Net 45'), ('net60', 'Net 60'), ('due_on_receipt', 'Due on Receipt'), ('custom', 'Custom')], default='net30', max_length=20)),
                ('custom_payment_terms', models.IntegerField(blank=True, help_text='Days until payment is due', null=True)),
                ('credit_limit', models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('opening_balance', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('bank_name', models.CharField(blank=True, max_length=100, null=True)),
                ('bank_account_number', models.CharField(blank=True, max_length=50, null=True)),
                ('bank_routing_number', models.CharField(blank=True, max_length=50, null=True)),
                ('bank_swift_code', models.CharField(blank=True, max_length=20, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='vendors_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['company_name'],
            },
        ),
        migrations.CreateModel(
            name='RecurringBill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('frequency', models.CharField(choices=[('weekly', 'Weekly'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('yearly', 'Yearly')], max_length=20)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('next_bill_date', models.DateField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('tax_rate', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('description', models.TextField()),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='Payables.expensecategory')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='recurring_bills', to='Payables.vendor')),
            ],
            options={
                'ordering': ['next_bill_date'],
            },
        ),
        migrations.AddField(
            model_name='purchaseorder',
            name='vendor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='purchase_orders', to='Payables.vendor'),
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_number', models.CharField(max_length=50, unique=True)),
                ('payment_date', models.DateField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)])),
                ('payment_method', models.CharField(choices=[('cash', 'Cash'), ('check', 'Check'), ('credit_card', 'Credit Card'), ('bank_transfer', 'Bank Transfer'), ('other', 'Other')], max_length=20)),
                ('reference_number', models.CharField(blank=True, max_length=100, null=True)),
                ('bank_charges', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='vendor_payments_created', to=settings.AUTH_USER_MODEL)),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='Payables.vendor')),
            ],
            options={
                'ordering': ['-payment_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expense_number', models.CharField(max_length=50, unique=True)),
                ('expense_date', models.DateField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)])),
                ('tax_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('payment_mode', models.CharField(choices=[('cash', 'Cash'), ('check', 'Check'), ('credit_card', 'Credit Card'), ('bank_transfer', 'Bank Transfer'), ('other', 'Other')], max_length=20)),
                ('reference_number', models.CharField(blank=True, max_length=100, null=True)),
                ('description', models.TextField()),
                ('is_billable', models.BooleanField(default=False)),
                ('status', models.CharField(choices=[('recorded', 'Recorded'), ('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('reimbursed', 'Reimbursed')], default='recorded', max_length=20)),
                ('receipt', models.FileField(blank=True, null=True, upload_to='expense_receipts/')),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='expenses_created', to=settings.AUTH_USER_MODEL)),
                ('customer', models.ForeignKey(blank=True, help_text='If billable to customer', null=True, on_delete=django.db.models.deletion.SET_NULL, to='invoicing.customer')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='Payables.expensecategory')),
                ('vendor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='expenses', to='Payables.vendor')),
            ],
            options={
                'ordering': ['-expense_date', '-created_at'],
            },
        ),
        migrations.AddField(
            model_name='bill',
            name='vendor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bills', to='Payables.vendor'),
        ),
        migrations.CreateModel(
            name='PaymentAllocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)])),
                ('bill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_allocations', to='Payables.bill')),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allocations', to='Payables.payment')),
            ],
            options={
                'unique_together': {('payment', 'bill')},
            },
        ),
    ]

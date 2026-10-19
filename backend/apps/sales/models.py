import uuid
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.core.models import LegalEntity, Branch, Warehouse, Partner, Product, UnitOfMeasure
from apps.inventory.models import Batch, StockBalance, InventoryService
from apps.accounting.models import Account, JournalEntry, JournalItem, BankCashAccount

User = get_user_model()


class SalesQuotation(models.Model):
    """Price quotation and commercial proposal to agricultural customer."""
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('SENT', _('Sent to Client')),
        ('ACCEPTED', _('Accepted')),
        ('REJECTED', _('Rejected')),
        ('CONVERTED', _('Converted to Sales Order')),
    ]
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.CASCADE, related_name='quotations')
    quotation_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name='quotations', limit_choices_to={'partner_type__in': ['CUSTOMER', 'BOTH']})
    quotation_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-quotation_date']
        verbose_name = _('Sales Quotation')
        verbose_name_plural = _('Sales Quotations')

    def __str__(self):
        return f"{self.quotation_number} - {self.customer.name_ar} [{self.get_status_display()}]"


class SalesQuotationItem(models.Model):
    quotation = models.ForeignKey(SalesQuotation, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='+')
    quantity = models.DecimalField(max_digits=16, decimal_places=4)
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='+')
    unit_price = models.DecimalField(max_digits=16, decimal_places=4)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    tax_rate = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.1400'))

    @property
    def line_subtotal(self) -> Decimal:
        gross = self.quantity * self.unit_price
        disc = gross * (self.discount_percent / Decimal('100.0'))
        return (gross - disc).quantize(Decimal('0.01'))

    @property
    def line_tax(self) -> Decimal:
        return (self.line_subtotal * self.tax_rate).quantize(Decimal('0.01'))

    @property
    def line_total(self) -> Decimal:
        return self.line_subtotal + self.line_tax


class SalesOrder(models.Model):
    """Customer Sales Order subject to credit limits and inventory allocation."""
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('CONFIRMED', _('Confirmed / Approved')),
        ('DELIVERED_PARTIAL', _('Partially Delivered')),
        ('DELIVERED_FULL', _('Fully Delivered')),
        ('CANCELLED', _('Cancelled')),
    ]
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.CASCADE, related_name='sales_orders')
    so_number = models.CharField(max_length=50, unique=True)
    quotation = models.ForeignKey(SalesQuotation, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_orders')
    customer = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name='sales_orders')
    order_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))

    # Credit Overrides
    credit_override = models.BooleanField(default=False)
    credit_override_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='credit_overrides')
    credit_override_reason = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-order_date', '-id']
        verbose_name = _('Sales Order')
        verbose_name_plural = _('Sales Orders')

    def __str__(self):
        return f"{self.so_number} - {self.customer.name_ar} [{self.get_status_display()}]"

    def recalculate_totals(self):
        sub = sum((item.line_subtotal for item in self.items.all()), Decimal('0.00'))
        tax = sum((item.line_tax for item in self.items.all()), Decimal('0.00'))
        self.subtotal = sub
        self.tax_amount = tax
        self.total_amount = sub + tax
        self.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])

    def check_credit_limit(self):
        """Validates customer credit exposure against allowed credit limit."""
        if self.customer.credit_limit <= Decimal('0.00'):
            return # Unlimited / cash customer

        # Outstanding posted unpaid invoices
        unpaid_invoices = SalesInvoice.objects.filter(
            customer=self.customer, status='POSTED'
        )
        current_debt = sum((inv.balance_due for inv in unpaid_invoices), Decimal('0.00'))
        new_total_exposure = current_debt + self.total_amount

        if new_total_exposure > self.customer.credit_limit:
            if not self.credit_override:
                raise ValidationError(
                    _("Credit limit exceeded: Customer %(cust)s has credit limit of %(lim)s EGP. "
                      "Current debt is %(debt)s EGP and new order is %(ord)s EGP (Total Exposure: %(exp)s EGP). "
                      "Requires authorized credit override.") % {
                        'cust': self.customer.name_ar,
                        'lim': self.customer.credit_limit,
                        'debt': current_debt,
                        'ord': self.total_amount,
                        'exp': new_total_exposure
                    }
                )

    def confirm(self):
        if self.status != 'DRAFT':
            raise ValidationError(_('Only draft orders can be confirmed.'))
        self.check_credit_limit()
        self.status = 'CONFIRMED'
        self.save(update_fields=['status'])


class SalesOrderItem(models.Model):
    """Line item in a Sales Order."""
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='+')
    quantity_ordered = models.DecimalField(max_digits=16, decimal_places=4)
    quantity_delivered = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0.0000'))
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='+')
    unit_price = models.DecimalField(max_digits=16, decimal_places=4)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    tax_rate = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.1400'))

    class Meta:
        verbose_name = _('Sales Order Item')
        verbose_name_plural = _('Sales Order Items')

    @property
    def line_subtotal(self) -> Decimal:
        gross = self.quantity_ordered * self.unit_price
        disc = gross * (self.discount_percent / Decimal('100.0'))
        return (gross - disc).quantize(Decimal('0.01'))

    @property
    def line_tax(self) -> Decimal:
        return (self.line_subtotal * self.tax_rate).quantize(Decimal('0.01'))

    @property
    def line_total(self) -> Decimal:
        return self.line_subtotal + self.line_tax


class SalesDelivery(models.Model):
    """Warehouse dispatch / Goods Issue to customer."""
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('DISPATCHED', _('Dispatched / Issued from Stock')),
        ('CANCELLED', _('Cancelled')),
    ]
    delivery_number = models.CharField(max_length=50, unique=True)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name='deliveries')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='sales_deliveries')
    delivery_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    dispatched_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Sales Delivery')
        verbose_name_plural = _('Sales Deliveries')

    def __str__(self):
        return f"{self.delivery_number} (SO: {self.sales_order.so_number})"

    @transaction.atomic
    def dispatch(self, user=None):
        """
        Dispatches goods:
        1. Checks batch validity (must be RELEASED and non-expired).
        2. Deducts inventory balance via perpetual ledger.
        3. Updates Sales Order delivered quantities.
        4. Posts Cost of Goods Sold (COGS) Journal Entry:
           Debit: COGS (5101)
           Credit: Finished Goods Inventory (1204)
        """
        if self.status != 'DRAFT':
            raise ValidationError(_('Only draft deliveries can be dispatched.'))

        so = self.sales_order
        total_cogs_value = Decimal('0.00')

        for item in self.items.all():
            so_item = so.items.filter(product=item.product).first()
            if not so_item:
                raise ValidationError(_('Product %s not part of the sales order.') % item.product.code)

            if so_item.quantity_delivered + item.quantity > so_item.quantity_ordered:
                raise ValidationError(
                    _("Cannot over-deliver product %(prod)s. Ordered: %(ord)s, Already delivered: %(del)s, Requested: %(req)s") % {
                        'prod': item.product.code, 'ord': so_item.quantity_ordered,
                        'del': so_item.quantity_delivered, 'req': item.quantity
                    }
                )

            # Issue inventory movement using perpetual ledger
            # Enforces that item.batch is RELEASED and not expired
            m = InventoryService.record_movement(
                movement_type='ISSUE_SALES',
                product=item.product,
                warehouse=self.warehouse,
                quantity=-item.quantity, # Negative for dispatch
                uom=item.uom,
                unit_cost=item.product.standard_cost, # Or moving average cost
                source_document=self.delivery_number,
                batch=item.batch,
                user=user,
                notes=f"Sales Delivery for SO {so.so_number} to {so.customer.name_ar}"
            )
            total_cogs_value += m.total_cost

            # Update delivered quantity on SO line
            so_item.quantity_delivered += item.quantity
            so_item.save(update_fields=['quantity_delivered'])

        # Update SO overall delivery status
        all_delivered = all(i.quantity_delivered >= i.quantity_ordered for i in so.items.all())
        any_delivered = any(i.quantity_delivered > Decimal('0') for i in so.items.all())
        if all_delivered:
            so.status = 'DELIVERED_FULL'
        elif any_delivered:
            so.status = 'DELIVERED_PARTIAL'
        so.save(update_fields=['status'])

        # Post COGS Journal Entry
        self._post_cogs_journal(total_cogs_value, user)

        self.status = 'DISPATCHED'
        self.dispatched_by = user
        self.save()

    def _post_cogs_journal(self, total_cogs: Decimal, user):
        if total_cogs <= Decimal('0.00'):
            return

        cogs_acc, _ = Account.objects.get_or_create(
            code='5101',
            defaults={'name_ar': 'تكلفة البضاعة المباعة', 'name_en': 'Cost of Goods Sold (COGS)', 'account_type': 'EXPENSE'}
        )
        fg_inventory_acc, _ = Account.objects.get_or_create(
            code='1204',
            defaults={'name_ar': 'مخزون الإنتاج التام', 'name_en': 'Finished Goods Inventory', 'account_type': 'ASSET'}
        )

        entry = JournalEntry.objects.create(
            legal_entity=self.sales_order.legal_entity,
            entry_number=f"JRN-COGS-{self.delivery_number}",
            entry_date=self.delivery_date,
            status='DRAFT',
            reference_document=self.delivery_number,
            idempotency_key=f"POST-COGS-{self.delivery_number}",
            memo=f"Cost of Goods Sold for Delivery {self.delivery_number} (Customer: {self.sales_order.customer.name_ar})"
        )
        JournalItem.objects.create(
            entry=entry, account=cogs_acc, debit=total_cogs, credit=Decimal('0.00'),
            memo=f"Debit: COGS for {self.delivery_number}"
        )
        JournalItem.objects.create(
            entry=entry, account=fg_inventory_acc, debit=Decimal('0.00'), credit=total_cogs,
            memo=f"Credit: Finished Goods Inventory for {self.delivery_number}"
        )
        entry.post(user=user)


class SalesDeliveryItem(models.Model):
    """Line item in a Sales Delivery."""
    delivery = models.ForeignKey(SalesDelivery, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='+')
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name='sales_delivery_items')
    quantity = models.DecimalField(max_digits=16, decimal_places=4)
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='+')

    class Meta:
        verbose_name = _('Sales Delivery Item')
        verbose_name_plural = _('Sales Delivery Items')


class SalesInvoice(models.Model):
    """Sales Tax Invoice adhering to Egyptian Tax Law (14% VAT, 1% WHT)."""
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('POSTED', _('Posted')),
        ('PAID', _('Paid')),
        ('CANCELLED', _('Cancelled')),
    ]
    invoice_number = models.CharField(max_length=50, unique=True)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name='invoices')
    delivery = models.ForeignKey(SalesDelivery, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    customer = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name='sales_invoices')
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    subtotal = models.DecimalField(max_digits=18, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text=_('Output VAT 14%'))
    wht_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text=_('Withholding Tax 1% deducted by customer'))
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)
    amount_collected = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date']
        verbose_name = _('Sales Tax Invoice')
        verbose_name_plural = _('Sales Tax Invoices')

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name_ar} (Total: {self.total_amount} EGP)"

    @property
    def balance_due(self) -> Decimal:
        return self.total_amount - self.amount_collected

    @transaction.atomic
    def post(self, user=None):
        """
        Posts Sales Invoice:
        Posts balancing double-entry journal:
        Debit: Customer AR (1101) [Net after WHT]
        Debit: WHT Tax Deducted by Customer (1105) [1% asset receivable from ETA]
        Credit: Sales Revenue (4101)
        Credit: Output VAT Payable (2201) [14% liability to ETA]
        """
        if self.status != 'DRAFT':
            raise ValidationError(_('Only draft invoices can be posted.'))

        ar_customer_acc, _ = Account.objects.get_or_create(
            code='1101',
            defaults={'name_ar': 'العملاء وأوراق القبض', 'name_en': 'Accounts Receivable - Customers', 'account_type': 'ASSET'}
        )
        wht_receivable_acc, _ = Account.objects.get_or_create(
            code='1105',
            defaults={'name_ar': 'ضريبة الخصم والإضافة المستحقة (أرباح تجارية)', 'name_en': 'Withholding Tax Receivable', 'account_type': 'ASSET'}
        )
        revenue_acc, _ = Account.objects.get_or_create(
            code='4101',
            defaults={'name_ar': 'إيرادات مبيعات المنتجات الكيميائية والأسمدة', 'name_en': 'Sales Revenue', 'account_type': 'REVENUE'}
        )
        output_vat_acc, _ = Account.objects.get_or_create(
            code='2201',
            defaults={'name_ar': 'ضريبة القيمة المضافة - مخرجات', 'name_en': 'Output VAT Payable', 'account_type': 'LIABILITY'}
        )

        entry = JournalEntry.objects.create(
            legal_entity=self.sales_order.legal_entity,
            entry_number=f"JRN-SINV-{self.invoice_number}",
            entry_date=self.invoice_date,
            status='DRAFT',
            reference_document=self.invoice_number,
            idempotency_key=f"POST-SINV-{self.invoice_number}",
            memo=f"Sales Invoice {self.invoice_number} - {self.customer.name_ar}"
        )

        # Debits
        net_receivable = self.total_amount - self.wht_amount
        JournalItem.objects.create(
            entry=entry, account=ar_customer_acc, debit=net_receivable, credit=Decimal('0.00'),
            partner=self.customer,
            memo=f"Accounts Receivable: {self.customer.name_ar} (Net after WHT)"
        )
        if self.wht_amount > Decimal('0.00'):
            JournalItem.objects.create(
                entry=entry, account=wht_receivable_acc, debit=self.wht_amount, credit=Decimal('0.00'),
                memo=f"WHT 1% (أرباح تجارية) Deducted by Customer on {self.invoice_number}"
            )

        # Credits
        JournalItem.objects.create(
            entry=entry, account=revenue_acc, debit=Decimal('0.00'), credit=self.subtotal,
            memo=f"Sales Revenue from {self.invoice_number}"
        )
        if self.vat_amount > Decimal('0.00'):
            JournalItem.objects.create(
                entry=entry, account=output_vat_acc, debit=Decimal('0.00'), credit=self.vat_amount,
                memo=f"Output VAT 14% on {self.invoice_number}"
            )

        entry.post(user=user)

        self.status = 'POSTED'
        self.save()


class CustomerReceipt(models.Model):
    """Receipt Voucher for cash or bank collection from customer."""
    receipt_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name='receipts')
    sales_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='collections')
    bank_cash_account = models.ForeignKey(BankCashAccount, on_delete=models.PROTECT, related_name='customer_collections')
    collection_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-collection_date']
        verbose_name = _('Customer Receipt')
        verbose_name_plural = _('Customer Receipts')

    @transaction.atomic
    def post(self, user=None):
        if self.amount <= Decimal('0.00'):
            raise ValidationError(_('Collection amount must be greater than zero.'))
        if self.amount > self.sales_invoice.balance_due:
            raise ValidationError(
                _('Collection amount %(amt)s exceeds invoice balance due %(due)s.') % {
                    'amt': self.amount, 'due': self.sales_invoice.balance_due
                }
            )

        ar_customer_acc, _ = Account.objects.get_or_create(
            code='1101',
            defaults={'name_ar': 'العملاء وأوراق القبض', 'name_en': 'Accounts Receivable - Customers', 'account_type': 'ASSET'}
        )

        entry = JournalEntry.objects.create(
            legal_entity=self.sales_invoice.sales_order.legal_entity,
            entry_number=f"JRN-CRCP-{self.receipt_number}",
            entry_date=self.collection_date,
            status='DRAFT',
            reference_document=self.receipt_number,
            idempotency_key=f"POST-CRCP-{self.receipt_number}",
            memo=f"Collection of {self.amount} EGP from {self.customer.name_ar} for Invoice {self.sales_invoice.invoice_number}"
        )
        # Debit Bank/Cash (Asset increase)
        JournalItem.objects.create(
            entry=entry, account=self.bank_cash_account.gl_account, debit=self.amount, credit=Decimal('0.00'),
            memo=f"Deposit into {self.bank_cash_account.name_ar}"
        )
        # Credit AR (Asset decrease)
        JournalItem.objects.create(
            entry=entry, account=ar_customer_acc, debit=Decimal('0.00'), credit=self.amount,
            partner=self.customer,
            memo=f"Collection from {self.customer.name_ar}"
        )
        entry.post(user=user)

        self.sales_invoice.amount_collected += self.amount
        if self.sales_invoice.amount_collected >= self.sales_invoice.total_amount:
            self.sales_invoice.status = 'PAID'
        self.sales_invoice.save()
        self.save()

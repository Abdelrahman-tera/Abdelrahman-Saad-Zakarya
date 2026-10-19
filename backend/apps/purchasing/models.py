import uuid
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.core.models import LegalEntity, Branch, Warehouse, Partner, Product, UnitOfMeasure
from apps.inventory.models import Batch, InventoryService
from apps.accounting.models import Account, JournalEntry, JournalItem, BankCashAccount

User = get_user_model()


class PurchaseOrder(models.Model):
    """Purchase Order to chemical raw material and packaging suppliers."""
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('APPROVED', _('Approved / Confirmed')),
        ('RECEIVED_PARTIAL', _('Partially Received')),
        ('RECEIVED_FULL', _('Fully Received')),
        ('CANCELLED', _('Cancelled')),
    ]
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.CASCADE, related_name='purchase_orders')
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name='purchase_orders', limit_choices_to={'partner_type__in': ['SUPPLIER', 'BOTH']})
    order_date = models.DateField(default=timezone.now)
    expected_delivery_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=10, default='EGP')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))

    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_pos')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-order_date', '-id']
        verbose_name = _('Purchase Order')
        verbose_name_plural = _('Purchase Orders')

    def __str__(self):
        return f"{self.po_number} - {self.supplier.name_ar} [{self.get_status_display()}]"

    def recalculate_totals(self):
        sub = sum((item.total_price for item in self.items.all()), Decimal('0.00'))
        tax = sum((item.tax_amount for item in self.items.all()), Decimal('0.00'))
        self.subtotal = sub
        self.tax_amount = tax
        self.total_amount = sub + tax
        self.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])


class PurchaseOrderItem(models.Model):
    """Line item in a Purchase Order."""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='+')
    quantity_ordered = models.DecimalField(max_digits=16, decimal_places=4)
    quantity_received = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0.0000'))
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='+')
    unit_price = models.DecimalField(max_digits=16, decimal_places=4)
    tax_rate = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal('0.1400'), help_text=_('Standard Egyptian VAT 14%'))

    class Meta:
        verbose_name = _('Purchase Order Item')
        verbose_name_plural = _('Purchase Order Items')

    @property
    def total_price(self) -> Decimal:
        return (self.quantity_ordered * self.unit_price).quantize(Decimal('0.01'))

    @property
    def tax_amount(self) -> Decimal:
        return (self.total_price * self.tax_rate).quantize(Decimal('0.01'))


class GoodsReceipt(models.Model):
    """Goods Received Note (GRN) / Warehouse delivery receipt."""
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('POSTED', _('Posted to Stock')),
        ('CANCELLED', _('Cancelled')),
    ]
    grn_number = models.CharField(max_length=50, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name='goods_receipts')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='goods_receipts')
    receipt_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Goods Receipt Note')
        verbose_name_plural = _('Goods Receipt Notes')

    def __str__(self):
        return f"{self.grn_number} (PO: {self.purchase_order.po_number})"

    @transaction.atomic
    def post(self, user=None):
        """
        Posts GRN:
        1. Validates quantities against PO.
        2. Creates Batch records in QUARANTINE state for incoming chemical materials.
        3. Updates Perpetual Stock Ledger and on-hand balances.
        4. Updates Purchase Order received quantities and status.
        5. Posts interim clearing journal entry.
        """
        if self.status != 'DRAFT':
            raise ValidationError(_('Only draft receipts can be posted.'))

        po = self.purchase_order
        total_receipt_value = Decimal('0.00')

        for item in self.items.all():
            if item.quantity_accepted < Decimal('0.0000'):
                raise ValidationError(_('Accepted quantity cannot be negative.'))
            if item.quantity_accepted + item.quantity_rejected != item.quantity_received:
                raise ValidationError(_('Accepted quantity + Rejected quantity must equal total received quantity.'))

            po_item = po.items.filter(product=item.product).first()
            if not po_item:
                raise ValidationError(_('Product %s not found in original purchase order.') % item.product.code)

            # Prevent over-receipt beyond tolerance (e.g. max 10% over-delivery)
            max_permitted = po_item.quantity_ordered * Decimal('1.10')
            if po_item.quantity_received + item.quantity_accepted > max_permitted:
                raise ValidationError(
                    _("Over-receipt violation: Product %(prod)s ordered %(ord)s, already received %(rec)s, attempting to receive %(new)s.") % {
                        'prod': item.product.code, 'ord': po_item.quantity_ordered,
                        'rec': po_item.quantity_received, 'new': item.quantity_accepted
                    }
                )

            # Create Batch for chemical traceability
            mfg_date = item.manufacturing_date or timezone.now().date()
            from datetime import timedelta
            exp_date = item.expiry_date or (mfg_date + timedelta(days=item.product.standard_shelf_life_days))
            batch, _ = Batch.objects.get_or_create(
                product=item.product,
                batch_number=item.batch_number,
                defaults={
                    'supplier_lot_number': item.supplier_lot_number,
                    'manufacturing_date': mfg_date,
                    'expiry_date': exp_date,
                    'status': 'QUARANTINE', # Defaults to quarantine awaiting QC inspection
                    'initial_quantity': item.quantity_accepted,
                    'uom': item.uom,
                }
            )

            # Record perpetual stock movement for accepted quantity
            if item.quantity_accepted > Decimal('0.0000'):
                unit_cost = po_item.unit_price
                m = InventoryService.record_movement(
                    movement_type='RECEIPT_PURCHASE',
                    product=item.product,
                    warehouse=self.warehouse,
                    quantity=item.quantity_accepted,
                    uom=item.uom,
                    unit_cost=unit_cost,
                    source_document=self.grn_number,
                    batch=batch,
                    user=user,
                    notes=f"Receipt from PO {po.po_number}",
                    allow_quarantine_movement=True
                )
                total_receipt_value += m.total_cost

            # Update PO item received quantity
            po_item.quantity_received += item.quantity_accepted
            po_item.save(update_fields=['quantity_received'])

        # Update PO status
        all_received = all(i.quantity_received >= i.quantity_ordered for i in po.items.all())
        any_received = any(i.quantity_received > Decimal('0') for i in po.items.all())
        if all_received:
            po.status = 'RECEIVED_FULL'
        elif any_received:
            po.status = 'RECEIVED_PARTIAL'
        po.save(update_fields=['status'])

        # Create balanced accounting journal entry (Inventory Clearing)
        self._post_accounting_journal(total_receipt_value, user)

        self.status = 'POSTED'
        self.received_by = user
        self.save()

    def _post_accounting_journal(self, total_value: Decimal, user):
        """Posts balanced double-entry journal for received inventory interim clearing."""
        if total_value <= Decimal('0.00'):
            return

        interim_stock_acc, _ = Account.objects.get_or_create(
            code='1209',
            defaults={'name_ar': 'وسيط استلام البضائع والمواد', 'name_en': 'Goods Received Interim Clearing', 'account_type': 'ASSET'}
        )
        interim_ap_acc, _ = Account.objects.get_or_create(
            code='2109',
            defaults={'name_ar': 'وسيط فواتير الموردين غير المستلمة', 'name_en': 'Unbilled Supplier Accrual', 'account_type': 'LIABILITY'}
        )

        entry = JournalEntry.objects.create(
            legal_entity=self.purchase_order.legal_entity,
            entry_number=f"JRN-GRN-{self.grn_number}",
            entry_date=self.receipt_date,
            status='DRAFT',
            reference_document=self.grn_number,
            idempotency_key=f"POST-GRN-{self.grn_number}",
            memo=f"Inventory Receipt from PO {self.purchase_order.po_number}"
        )
        JournalItem.objects.create(
            entry=entry, account=interim_stock_acc, debit=total_value, credit=Decimal('0.00'),
            memo=f"Debit: Stock Clearing for {self.grn_number}"
        )
        JournalItem.objects.create(
            entry=entry, account=interim_ap_acc, debit=Decimal('0.00'), credit=total_value,
            partner=self.purchase_order.supplier,
            memo=f"Credit: AP Accrual for {self.grn_number}"
        )
        entry.post(user=user)


class GoodsReceiptItem(models.Model):
    """Line item in a Goods Receipt Note."""
    goods_receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='+')
    quantity_received = models.DecimalField(max_digits=16, decimal_places=4)
    quantity_accepted = models.DecimalField(max_digits=16, decimal_places=4)
    quantity_rejected = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0.0000'))
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='+')
    batch_number = models.CharField(max_length=100)
    supplier_lot_number = models.CharField(max_length=100, blank=True, default='')
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = _('Goods Receipt Item')
        verbose_name_plural = _('Goods Receipt Items')


class SupplierInvoice(models.Model):
    """Supplier Tax Invoice with 3-Way Matching and Egyptian Tax Handling (VAT 14%, WHT 1%)."""
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('POSTED', _('Posted')),
        ('PAID', _('Paid')),
        ('CANCELLED', _('Cancelled')),
    ]
    invoice_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name='supplier_invoices')
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name='supplier_invoices')
    goods_receipt = models.ForeignKey(GoodsReceipt, on_delete=models.SET_NULL, null=True, blank=True, related_name='supplier_invoices')
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    subtotal = models.DecimalField(max_digits=18, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text=_('Input VAT 14%'))
    wht_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text=_('Withholding tax (خصم وأرباح تجارية) 1%'))
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)

    amount_paid = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date']
        verbose_name = _('Supplier Invoice')
        verbose_name_plural = _('Supplier Invoices')

    def __str__(self):
        return f"{self.invoice_number} - {self.supplier.name_ar} (Total: {self.total_amount} EGP)"

    @property
    def balance_due(self) -> Decimal:
        return self.total_amount - self.amount_paid

    @transaction.atomic
    def post(self, user=None):
        """
        Posts Supplier Invoice:
        1. Performs 3-way match verification.
        2. Posts balanced double-entry accounting entry:
           Debit: Interim AP Accrual (2109)
           Debit: Input VAT Tax Receivable (1205)
           Credit: Supplier Payable AP (2101)
           Credit: Withholding Tax Payable WHT (2106)
        """
        if self.status != 'DRAFT':
            raise ValidationError(_('Only draft invoices can be posted.'))

        # 3-Way Match Check
        if self.goods_receipt:
            grn_total = sum(
                (item.quantity_accepted * self.purchase_order.items.get(product=item.product).unit_price
                 for item in self.goods_receipt.items.all()),
                Decimal('0.00')
            )
            # Tolerance threshold e.g. difference <= 1 EGP due to rounding
            if abs(self.subtotal - grn_total) > Decimal('5.00'):
                raise ValidationError(
                    _("3-Way Match discrepancy: Invoice Subtotal %(inv)s does not match Goods Receipt value %(grn)s") % {
                        'inv': self.subtotal, 'grn': grn_total
                    }
                )

        # Build Accounting Journal Entry
        interim_ap_acc, _ = Account.objects.get_or_create(
            code='2109',
            defaults={'name_ar': 'وسيط فواتير الموردين غير المستلمة', 'name_en': 'Unbilled Supplier Accrual', 'account_type': 'LIABILITY'}
        )
        input_vat_acc, _ = Account.objects.get_or_create(
            code='1205',
            defaults={'name_ar': 'ضريبة القيمة المضافة - مدخلات', 'name_en': 'Input VAT Recoverable', 'account_type': 'ASSET'}
        )
        ap_supplier_acc, _ = Account.objects.get_or_create(
            code='2101',
            defaults={'name_ar': 'الموردون وأوراق الدفع', 'name_en': 'Accounts Payable - Suppliers', 'account_type': 'LIABILITY'}
        )
        wht_payable_acc, _ = Account.objects.get_or_create(
            code='2106',
            defaults={'name_ar': 'ضريبة الخصم والتحصيل من المنبع - دائنة', 'name_en': 'Withholding Tax Payable', 'account_type': 'LIABILITY'}
        )

        entry = JournalEntry.objects.create(
            legal_entity=self.purchase_order.legal_entity,
            entry_number=f"JRN-SINV-{self.invoice_number}",
            entry_date=self.invoice_date,
            status='DRAFT',
            reference_document=self.invoice_number,
            idempotency_key=f"POST-SINV-{self.invoice_number}",
            memo=f"Supplier Invoice {self.invoice_number} - {self.supplier.name_ar}"
        )

        # Debits
        JournalItem.objects.create(
            entry=entry, account=interim_ap_acc, debit=self.subtotal, credit=Decimal('0.00'),
            memo=f"Clear Unbilled AP Accrual for {self.invoice_number}"
        )
        if self.vat_amount > Decimal('0.00'):
            JournalItem.objects.create(
                entry=entry, account=input_vat_acc, debit=self.vat_amount, credit=Decimal('0.00'),
                memo=f"Input VAT 14% on {self.invoice_number}"
            )

        # Credits
        # Net supplier payable = Subtotal + VAT - WHT
        net_payable = self.subtotal + self.vat_amount - self.wht_amount
        JournalItem.objects.create(
            entry=entry, account=ap_supplier_acc, debit=Decimal('0.00'), credit=net_payable,
            partner=self.supplier,
            memo=f"Accounts Payable to {self.supplier.name_ar} (Net after WHT)"
        )
        if self.wht_amount > Decimal('0.00'):
            JournalItem.objects.create(
                entry=entry, account=wht_payable_acc, debit=Decimal('0.00'), credit=self.wht_amount,
                memo=f"Withholding Tax 1% (خصم منبع) on {self.invoice_number}"
            )

        entry.post(user=user)

        self.status = 'POSTED'
        self.save()


class SupplierPayment(models.Model):
    """Payment voucher to supplier settling full or partial invoices."""
    payment_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Partner, on_delete=models.PROTECT, related_name='payments')
    supplier_invoice = models.ForeignKey(SupplierInvoice, on_delete=models.CASCADE, related_name='payments')
    bank_cash_account = models.ForeignKey(BankCashAccount, on_delete=models.PROTECT, related_name='supplier_payments')
    payment_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']
        verbose_name = _('Supplier Payment')
        verbose_name_plural = _('Supplier Payments')

    @transaction.atomic
    def post(self, user=None):
        if self.amount <= Decimal('0.00'):
            raise ValidationError(_('Payment amount must be greater than zero.'))
        if self.amount > self.supplier_invoice.balance_due:
            raise ValidationError(_('Payment amount %(amt)s exceeds invoice balance due %(due)s.') % {
                'amt': self.amount, 'due': self.supplier_invoice.balance_due
            })

        ap_supplier_acc, _ = Account.objects.get_or_create(
            code='2101',
            defaults={'name_ar': 'الموردون وأوراق الدفع', 'name_en': 'Accounts Payable - Suppliers', 'account_type': 'LIABILITY'}
        )

        entry = JournalEntry.objects.create(
            legal_entity=self.supplier_invoice.purchase_order.legal_entity,
            entry_number=f"JRN-SPAY-{self.payment_number}",
            entry_date=self.payment_date,
            status='DRAFT',
            reference_document=self.payment_number,
            idempotency_key=f"POST-SPAY-{self.payment_number}",
            memo=f"Payment of {self.amount} EGP for Invoice {self.supplier_invoice.invoice_number}"
        )
        # Debit AP (reduce liability)
        JournalItem.objects.create(
            entry=entry, account=ap_supplier_acc, debit=self.amount, credit=Decimal('0.00'),
            partner=self.supplier,
            memo=f"Reduce AP for {self.supplier.name_ar}"
        )
        # Credit Bank/Cash (reduce asset)
        JournalItem.objects.create(
            entry=entry, account=self.bank_cash_account.gl_account, debit=Decimal('0.00'), credit=self.amount,
            memo=f"Payment from {self.bank_cash_account.name_ar}"
        )
        entry.post(user=user)

        # Update invoice balance and status
        self.supplier_invoice.amount_paid += self.amount
        if self.supplier_invoice.amount_paid >= self.supplier_invoice.total_amount:
            self.supplier_invoice.status = 'PAID'
        self.supplier_invoice.save()
        self.save()

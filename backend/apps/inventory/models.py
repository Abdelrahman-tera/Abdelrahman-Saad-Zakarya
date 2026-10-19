import uuid
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.core.models import Product, Warehouse, StorageLocation, UnitOfMeasure

User = get_user_model()


class Batch(models.Model):
    """Chemical formulation or raw-material lot with strict lifecycle states."""
    BATCH_STATUS = [
        ('QUARANTINE', _('Quarantine (تحت الحجر / الفحص)')),
        ('RELEASED', _('Released / Approved (معتمد / مصرح بالاستخدام والصرف)')),
        ('QUALITY_HOLD', _('Quality Hold (موقوف مؤقتاً للجودة)')),
        ('REJECTED', _('Rejected (مرفوض / غير مطابق)')),
        ('EXPIRED', _('Expired (منتهي الصلاحية)')),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=100, db_index=True)
    supplier_lot_number = models.CharField(max_length=100, blank=True, default='')
    manufacturing_date = models.DateField(db_index=True)
    expiry_date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=BATCH_STATUS, default='QUARANTINE', db_index=True)

    initial_quantity = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0.0000'))
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='+')
    qc_released_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='released_batches')
    qc_released_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'batch_number')
        ordering = ['expiry_date', 'manufacturing_date']
        verbose_name = _('Batch / Lot')
        verbose_name_plural = _('Batches & Lots')

    def __str__(self):
        return f"{self.product.code} - Batch {self.batch_number} [{self.get_status_display()}]"

    def is_usable(self) -> bool:
        """Determines if batch can be issued for manufacturing or customer dispatch."""
        if self.status != 'RELEASED':
            return False
        if self.expiry_date <= timezone.now().date():
            return False
        return True


class StockBalance(models.Model):
    """Authoritative atomic on-hand stock balance per warehouse, location, and batch."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_balances')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_balances')
    storage_location = models.ForeignKey(StorageLocation, on_delete=models.CASCADE, null=True, blank=True, related_name='stock_balances')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True, blank=True, related_name='stock_balances')

    quantity_on_hand = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0.0000'))
    quantity_reserved = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0.0000'))
    valuation_unit_cost = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0.0000'))

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'warehouse', 'storage_location', 'batch')
        ordering = ['product', 'warehouse']
        verbose_name = _('Stock Balance')
        verbose_name_plural = _('Stock Balances')

    def __str__(self):
        batch_str = f" - Batch {self.batch.batch_number}" if self.batch else ""
        return f"{self.product.code} @ {self.warehouse.code}{batch_str}: OnHand={self.quantity_on_hand}, Avail={self.quantity_available}"

    @property
    def quantity_available(self) -> Decimal:
        return max(Decimal('0.0000'), self.quantity_on_hand - self.quantity_reserved)


class StockMovement(models.Model):
    """Authoritative perpetual stock ledger recording all material entries and exits."""
    MOVEMENT_TYPES = [
        ('RECEIPT_PURCHASE', _('Purchase Receipt (GRN)')),
        ('ISSUE_SALES', _('Sales Delivery Issue')),
        ('ISSUE_PRODUCTION', _('Production Material Issue / Consumption')),
        ('RECEIPT_PRODUCTION', _('Production Finished Goods Output')),
        ('TRANSFER_OUT', _('Internal Warehouse Transfer (Out)')),
        ('TRANSFER_IN', _('Internal Warehouse Transfer (In)')),
        ('SCRAP_LOSS', _('Production Scrap / Chemical Loss')),
        ('ADJUSTMENT_IN', _('Inventory Adjustment (Gain)')),
        ('ADJUSTMENT_OUT', _('Inventory Adjustment (Loss)')),
        ('RETURN_CUSTOMER', _('Customer Return')),
        ('RETURN_SUPPLIER', _('Supplier Return')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    movement_type = models.CharField(max_length=30, choices=MOVEMENT_TYPES, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='stock_movements')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='stock_movements')
    storage_location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, null=True, blank=True)
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, null=True, blank=True, related_name='stock_movements')

    quantity = models.DecimalField(max_digits=16, decimal_places=4, help_text=_('Quantity moved (positive for IN, negative for OUT)'))
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='+')
    unit_cost = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0.0000'))
    total_cost = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))

    source_document = models.CharField(max_length=100, db_index=True, help_text=_('Originating reference e.g. PO-001, SO-005, MO-102'))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('Stock Movement')
        verbose_name_plural = _('Perpetual Stock Ledger')

    def __str__(self):
        return f"{self.timestamp} - {self.get_movement_type_display()}: {self.product.code} ({self.quantity} {self.uom.code})"


class StockReservation(models.Model):
    """Reserves inventory for confirmed sales orders or released manufacturing orders."""
    RESERVATION_STATUS = [
        ('ACTIVE', _('Active')),
        ('CONSUMED', _('Consumed / Dispatched')),
        ('CANCELLED', _('Cancelled / Released')),
    ]
    source_document = models.CharField(max_length=100, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='reservations')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='reservations')
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, null=True, blank=True, related_name='reservations')
    quantity = models.DecimalField(max_digits=16, decimal_places=4)
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='+')
    status = models.CharField(max_length=20, choices=RESERVATION_STATUS, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Stock Reservation')
        verbose_name_plural = _('Stock Reservations')


class InventoryService:
    """Core inventory transactional engine ensuring ACID compliance, exact valuation, and FEFO picking."""

    @classmethod
    @transaction.atomic
    def record_movement(
        cls,
        movement_type: str,
        product: Product,
        warehouse: Warehouse,
        quantity: Decimal,
        uom: UnitOfMeasure,
        unit_cost: Decimal,
        source_document: str,
        batch: Batch = None,
        storage_location: StorageLocation = None,
        user=None,
        notes: str = '',
        allow_quarantine_movement: bool = False
    ) -> StockMovement:
        """
        Records a stock movement in the perpetual ledger and atomically updates on-hand balance.
        Positive quantity adds stock; negative quantity removes stock.
        """
        # Enforce batch quality & expiry gate for OUT movements
        if quantity < Decimal('0'):
            if batch:
                if not allow_quarantine_movement and not batch.is_usable():
                    raise ValidationError(
                        _("Cannot issue batch %(batch)s with status '%(status)s' or past expiry date (%(expiry)s).") % {
                            'batch': batch.batch_number,
                            'status': batch.get_status_display(),
                            'expiry': batch.expiry_date
                        }
                    )

        # Normalise quantity to product default UOM if needed
        qty_in_default = product.convert_quantity(abs(quantity), uom, product.default_uom)
        signed_qty = qty_in_default if quantity > Decimal('0') else -qty_in_default

        total_cost = (abs(signed_qty) * unit_cost).quantize(Decimal('0.01'))

        # Lock and update stock balance
        balance, created = StockBalance.objects.select_for_update().get_or_create(
            product=product,
            warehouse=warehouse,
            storage_location=storage_location,
            batch=batch,
            defaults={'quantity_on_hand': Decimal('0.0000'), 'valuation_unit_cost': unit_cost}
        )

        new_on_hand = balance.quantity_on_hand + signed_qty
        if new_on_hand < Decimal('0.0000'):
            raise ValidationError(
                _("Insufficient inventory for %(prod)s at %(wh)s. Available: %(avail)s, Requested: %(req)s") % {
                    'prod': product.code,
                    'wh': warehouse.code,
                    'avail': balance.quantity_on_hand,
                    'req': abs(signed_qty)
                }
            )

        # Perpetual moving weighted-average cost update for incoming stock
        if signed_qty > Decimal('0') and new_on_hand > Decimal('0'):
            existing_val = balance.quantity_on_hand * balance.valuation_unit_cost
            new_incoming_val = signed_qty * unit_cost
            balance.valuation_unit_cost = ((existing_val + new_incoming_val) / new_on_hand).quantize(Decimal('0.0001'))

        balance.quantity_on_hand = new_on_hand
        balance.save()

        # Create perpetual ledger entry
        movement = StockMovement.objects.create(
            movement_type=movement_type,
            product=product,
            warehouse=warehouse,
            storage_location=storage_location,
            batch=batch,
            quantity=signed_qty,
            uom=product.default_uom,
            unit_cost=unit_cost,
            total_cost=total_cost,
            source_document=source_document,
            user=user,
            notes=notes
        )
        return movement

    @classmethod
    @transaction.atomic
    def reserve_stock(
        cls,
        source_document: str,
        product: Product,
        warehouse: Warehouse,
        quantity: Decimal,
        uom: UnitOfMeasure,
        batch: Batch = None
    ) -> StockReservation:
        """
        Reserves available stock preventing overselling/double allocation.
        Uses select_for_update for strict concurrency safety.
        """
        qty_needed = product.convert_quantity(quantity, uom, product.default_uom)

        if batch:
            if not batch.is_usable():
                raise ValidationError(_("Cannot reserve unreleased or expired batch %s.") % batch.batch_number)
            balance = StockBalance.objects.select_for_update().filter(
                product=product, warehouse=warehouse, batch=batch
            ).first()
            if not balance or balance.quantity_available < qty_needed:
                avail = balance.quantity_available if balance else Decimal('0.0000')
                raise ValidationError(
                    _("Insufficient available stock for batch %(batch)s. Available: %(avail)s, Needed: %(req)s") % {
                        'batch': batch.batch_number, 'avail': avail, 'req': qty_needed
                    }
                )
            balance.quantity_reserved += qty_needed
            balance.save()
        else:
            # Auto FEFO selection
            fefo_batches = cls.pick_fefo_batches(product, warehouse, qty_needed)
            if not fefo_batches:
                raise ValidationError(_("No sufficient approved non-expired batches found for product %s.") % product.code)

            for b_info in fefo_batches:
                b = b_info['batch']
                b_qty = b_info['allocated_qty']
                bal = StockBalance.objects.select_for_update().get(
                    product=product, warehouse=warehouse, batch=b
                )
                bal.quantity_reserved += b_qty
                bal.save()

        return StockReservation.objects.create(
            source_document=source_document,
            product=product,
            warehouse=warehouse,
            batch=batch,
            quantity=qty_needed,
            uom=product.default_uom,
            status='ACTIVE'
        )

    @classmethod
    def pick_fefo_batches(cls, product: Product, warehouse: Warehouse, quantity: Decimal) -> list:
        """
        FEFO (First Expired, First Out) selection algorithm:
        Finds only RELEASED, non-expired batches sorted by expiry date ascending.
        """
        today = timezone.now().date()
        valid_balances = StockBalance.objects.filter(
            product=product,
            warehouse=warehouse,
            batch__status='RELEASED',
            batch__expiry_date__gt=today
        ).exclude(batch__isnull=True).order_by('batch__expiry_date')

        allocated = []
        remaining = quantity

        for bal in valid_balances:
            avail = bal.quantity_available
            if avail <= Decimal('0'):
                continue
            qty_from_batch = min(avail, remaining)
            allocated.append({
                'batch': bal.batch,
                'allocated_qty': qty_from_batch,
                'expiry_date': bal.batch.expiry_date
            })
            remaining -= qty_from_batch
            if remaining <= Decimal('0'):
                break

        if remaining > Decimal('0'):
            return [] # Insufficient FEFO inventory
        return allocated

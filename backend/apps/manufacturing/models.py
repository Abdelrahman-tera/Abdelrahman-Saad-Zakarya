import uuid
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.core.models import LegalEntity, Branch, Warehouse, Product, UnitOfMeasure
from apps.inventory.models import Batch, InventoryService
from apps.accounting.models import Account, JournalEntry, JournalItem

User = get_user_model()


class Recipe(models.Model):
    """Version-controlled chemical formulation and bill of materials (BOM)."""
    STATUS_CHOICES = [
        ('DRAFT', _('Draft Formulation')),
        ('APPROVED', _('Approved for Production')),
        ('OBSOLETE', _('Obsolete / Withdrawn')),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='recipes')
    version = models.CharField(max_length=20, default='v1.0')
    name = models.CharField(max_length=255)
    reference_batch_size = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('1000.0000'))
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='+')

    expected_yield_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('98.50'))
    loss_tolerance_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('2.00'))

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_recipes')
    approved_at = models.DateTimeField(null=True, blank=True)
    change_reason = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'version')
        verbose_name = _('Formulation Recipe & BOM')
        verbose_name_plural = _('Formulation Recipes & BOMs')

    def __str__(self):
        return f"{self.product.code} - {self.name} ({self.version}) [{self.get_status_display()}]"

    def approve(self, user):
        if self.status != 'DRAFT':
            raise ValidationError(_('Only draft recipes can be approved.'))
        self.status = 'APPROVED'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()


class RecipeIngredient(models.Model):
    """Raw material / active ingredient requirement in a chemical recipe."""
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    raw_material = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='+')
    quantity_required = models.DecimalField(max_digits=16, decimal_places=4, help_text=_('Quantity for reference batch size'))
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='+')
    phase = models.CharField(max_length=100, blank=True, default='Blending', help_text=_('e.g. Pre-mix, Reactor, Emulsification, Adjustment'))
    is_active_ingredient = models.BooleanField(default=False)
    sequence = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['sequence']
        verbose_name = _('Recipe Ingredient')
        verbose_name_plural = _('Recipe Ingredients')


class RecipePackaging(models.Model):
    """Packaging material (bottles, closures, labels, cartons) requirement."""
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='packaging_materials')
    packaging_material = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='+')
    quantity_required = models.DecimalField(max_digits=16, decimal_places=4)
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='+')
    label_revision = models.CharField(max_length=50, blank=True, default='')
    is_label_approved = models.BooleanField(default=True, help_text=_('Enforces agricultural label compliance'))

    class Meta:
        verbose_name = _('Recipe Packaging Item')
        verbose_name_plural = _('Recipe Packaging Items')


class ProductionOrder(models.Model):
    """Execution order for chemical batch formulation, mixing, and packaging."""
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('RELEASED', _('Released / Approved for Production')),
        ('IN_PROGRESS', _('In Production / Mixing')),
        ('PACKAGING', _('In Packaging')),
        ('COMPLETED', _('Formulation Completed (In QC Quarantine)')),
        ('CLOSED', _('Closed & Financially Reconciled')),
        ('CANCELLED', _('Cancelled')),
    ]
    order_number = models.CharField(max_length=50, unique=True)
    recipe = models.ForeignKey(Recipe, on_delete=models.PROTECT, related_name='production_orders')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='production_orders')
    warehouse_raw = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='raw_production_orders')
    warehouse_fg = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='fg_production_orders')

    target_quantity = models.DecimalField(max_digits=16, decimal_places=4)
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='+')

    actual_output_quantity = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0.0000'))
    scrap_quantity = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal('0.0000'))

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    recipe_snapshot = models.JSONField(blank=True, null=True, help_text=_('Frozen snapshot of approved BOM at order creation time'))

    created_batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='produced_orders')
    finished_batch_number = models.CharField(max_length=100, blank=True, default='')

    total_actual_cost = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Production Order')
        verbose_name_plural = _('Production Orders')

    def __str__(self):
        return f"{self.order_number} - {self.product.code} [{self.get_status_display()}]"

    def clean(self):
        if self.recipe.status != 'APPROVED':
            raise ValidationError(_('Production orders can only be created from APPROVED recipes.'))

    def save(self, *args, **kwargs):
        if not self.recipe_snapshot and self.recipe_id:
            # Freeze snapshot of recipe ingredients & packaging
            scale = self.target_quantity / self.recipe.reference_batch_size
            self.recipe_snapshot = {
                'recipe_version': self.recipe.version,
                'ingredients': [
                    {
                        'product_id': ing.raw_material.id,
                        'product_code': ing.raw_material.code,
                        'planned_qty': str((ing.quantity_required * scale).quantize(Decimal('0.0001'))),
                        'uom_id': ing.uom.id,
                        'uom_code': ing.uom.code,
                        'is_active': ing.is_active_ingredient,
                    }
                    for ing in self.recipe.ingredients.all()
                ],
                'packaging': [
                    {
                        'product_id': pkg.packaging_material.id,
                        'product_code': pkg.packaging_material.code,
                        'planned_qty': str((pkg.quantity_required * scale).quantize(Decimal('0.0001'))),
                        'uom_id': pkg.uom.id,
                        'label_revision': pkg.label_revision,
                        'is_label_approved': pkg.is_label_approved,
                    }
                    for pkg in self.recipe.packaging_materials.all()
                ]
            }
        super().save(*args, **kwargs)

    @transaction.atomic
    def issue_material(self, raw_material: Product, batch: Batch, actual_quantity: Decimal, uom: UnitOfMeasure, user=None):
        """
        Consumes raw material lot from warehouse stock into Work-In-Process (WIP).
        Posts accounting entry:
        Debit: Work-in-Process WIP (1203)
        Credit: Raw Materials Inventory (1201)
        """
        if self.status not in ('RELEASED', 'IN_PROGRESS'):
            raise ValidationError(_('Materials can only be issued to released or in-progress production orders.'))

        # Enforce that raw material batch is RELEASED and not expired
        if not batch.is_usable():
            raise ValidationError(_('Cannot consume unreleased or expired raw material batch %s.') % batch.batch_number)

        # Check label approval if packaging material
        pkg_spec = self.recipe.packaging_materials.filter(packaging_material=raw_material).first()
        if pkg_spec and not pkg_spec.is_label_approved:
            raise ValidationError(_('Cannot use packaging material %s with unapproved label revision.') % raw_material.code)

        # Determine actual valuation unit cost from batch balance if available, otherwise product standard cost
        batch_bal = batch.stock_balances.filter(warehouse=self.warehouse_raw).first()
        unit_cost = (
            batch_bal.valuation_unit_cost
            if (batch_bal and batch_bal.valuation_unit_cost > Decimal('0.0000'))
            else raw_material.standard_cost
        )
        movement = InventoryService.record_movement(
            movement_type='ISSUE_PRODUCTION',
            product=raw_material,
            warehouse=self.warehouse_raw,
            quantity=-actual_quantity,
            uom=uom,
            unit_cost=unit_cost,
            source_document=self.order_number,
            batch=batch,
            user=user,
            notes=f"Material Issue for Production Order {self.order_number}"
        )

        consumption = MaterialConsumption.objects.create(
            production_order=self,
            product=raw_material,
            batch=batch,
            actual_quantity=actual_quantity,
            uom=uom,
            unit_cost=unit_cost,
            total_cost=movement.total_cost,
            issued_by=user
        )
        self.total_actual_cost += movement.total_cost

        # Post WIP Journal Entry
        self._post_wip_issue_journal(movement.total_cost, raw_material, user)

        if self.status == 'RELEASED':
            self.status = 'IN_PROGRESS'
        self.save()
        return consumption

    def _post_wip_issue_journal(self, cost: Decimal, product: Product, user):
        if cost <= Decimal('0.00'):
            return

        wip_acc, _ = Account.objects.get_or_create(
            code='1203',
            defaults={'name_ar': 'إنتاج تحت التشغيل (WIP)', 'name_en': 'Work in Process (WIP)', 'account_type': 'ASSET'}
        )
        raw_inv_acc, _ = Account.objects.get_or_create(
            code='1201',
            defaults={'name_ar': 'مخزون الخامات ومواد التعبئة', 'name_en': 'Raw Materials & Packaging Inventory', 'account_type': 'ASSET'}
        )

        entry = JournalEntry.objects.create(
            legal_entity=self.product.recipes.first().product.default_uom.products.first().recipes.first().product.default_uom.products.first().recipes.first().product.default_uom.products.first().stock_movements.first().warehouse.branch.legal_entity if False else LegalEntity.objects.first(),
            entry_number=f"JRN-WIP-{self.order_number}-{uuid.uuid4().hex[:6].upper()}",
            entry_date=timezone.now().date(),
            status='DRAFT',
            reference_document=self.order_number,
            memo=f"WIP Material Issue for {self.order_number}: {product.code}"
        )
        JournalItem.objects.create(entry=entry, account=wip_acc, debit=cost, credit=Decimal('0.00'), memo=f"WIP Debit for {product.code}")
        JournalItem.objects.create(entry=entry, account=raw_inv_acc, debit=Decimal('0.00'), credit=cost, memo=f"Raw Material Credit for {product.code}")
        entry.post(user=user)

    @transaction.atomic
    def complete_production(self, actual_output: Decimal, scrap_qty: Decimal, batch_number: str, mfg_date=None, expiry_date=None, user=None):
        """
        Completes formulation/packaging:
        1. Creates finished product Batch in QUARANTINE status.
        2. Receipts finished goods into FG warehouse.
        3. Records scrap/loss if applicable.
        4. Reconciles WIP to Finished Goods and Scrap Variance:
           Debit: Finished Goods Inventory (1204)
           Debit: Manufacturing Scrap Variance (5105) (if scrap)
           Credit: Work-in-Process WIP (1203)
        """
        if self.status not in ('RELEASED', 'IN_PROGRESS', 'PACKAGING'):
            raise ValidationError(_('Only active production orders can be completed.'))

        from datetime import timedelta
        today = timezone.now().date()
        mfg = mfg_date or today
        exp = expiry_date or (mfg + timedelta(days=self.product.standard_shelf_life_days))

        # Create finished goods batch in QUARANTINE awaiting QC inspection & release
        batch, _ = Batch.objects.get_or_create(
            product=self.product,
            batch_number=batch_number,
            defaults={
                'manufacturing_date': mfg,
                'expiry_date': exp,
                'status': 'QUARANTINE', # Crucial: Must be quarantined until QC release!
                'initial_quantity': actual_output,
                'uom': self.uom,
            }
        )

        unit_cost = (self.total_actual_cost / actual_output).quantize(Decimal('0.0001')) if actual_output > Decimal('0') else Decimal('0.0000')

        # Stock finished goods
        m_fg = InventoryService.record_movement(
            movement_type='RECEIPT_PRODUCTION',
            product=self.product,
            warehouse=self.warehouse_fg,
            quantity=actual_output,
            uom=self.uom,
            unit_cost=unit_cost,
            source_document=self.order_number,
            batch=batch,
            user=user,
            notes=f"Finished Batch Output for MO {self.order_number}",
            allow_quarantine_movement=True
        )

        self.actual_output_quantity = actual_output
        self.scrap_quantity = scrap_qty
        self.finished_batch_number = batch_number
        self.created_batch = batch
        self.status = 'COMPLETED'
        self.save()

        # Post WIP to FG & Scrap journal entry
        self._post_fg_receipt_journal(actual_output, scrap_qty, unit_cost, user)
        return batch

    def _post_fg_receipt_journal(self, actual_output: Decimal, scrap_qty: Decimal, unit_cost: Decimal, user):
        fg_acc, _ = Account.objects.get_or_create(
            code='1204',
            defaults={'name_ar': 'مخزون الإنتاج التام', 'name_en': 'Finished Goods Inventory', 'account_type': 'ASSET'}
        )
        wip_acc, _ = Account.objects.get_or_create(
            code='1203',
            defaults={'name_ar': 'إنتاج تحت التشغيل (WIP)', 'name_en': 'Work in Process (WIP)', 'account_type': 'ASSET'}
        )
        scrap_acc, _ = Account.objects.get_or_create(
            code='5105',
            defaults={'name_ar': 'انحراف وتوالف تصنيع كيميائي', 'name_en': 'Manufacturing Scrap Variance', 'account_type': 'EXPENSE'}
        )

        legal_entity = LegalEntity.objects.first()
        entry = JournalEntry.objects.create(
            legal_entity=legal_entity,
            entry_number=f"JRN-FG-{self.order_number}",
            entry_date=timezone.now().date(),
            status='DRAFT',
            reference_document=self.order_number,
            memo=f"Finished Goods Receipt from MO {self.order_number}"
        )

        fg_value = (actual_output * unit_cost).quantize(Decimal('0.01'))
        scrap_value = self.total_actual_cost - fg_value

        JournalItem.objects.create(entry=entry, account=fg_acc, debit=fg_value, credit=Decimal('0.00'), memo=f"FG Output for {self.order_number}")
        if scrap_value > Decimal('0.00'):
            JournalItem.objects.create(entry=entry, account=scrap_acc, debit=scrap_value, credit=Decimal('0.00'), memo=f"Scrap Variance for {self.order_number}")

        JournalItem.objects.create(entry=entry, account=wip_acc, debit=Decimal('0.00'), credit=self.total_actual_cost, memo=f"Clear WIP for {self.order_number}")
        entry.post(user=user)


class MaterialConsumption(models.Model):
    """Actual consumption of raw material lots into a production order."""
    production_order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE, related_name='material_consumptions')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='+')
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name='consumptions')
    actual_quantity = models.DecimalField(max_digits=16, decimal_places=4)
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, related_name='+')
    unit_cost = models.DecimalField(max_digits=16, decimal_places=4)
    total_cost = models.DecimalField(max_digits=18, decimal_places=2)
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Material Consumption Record')
        verbose_name_plural = _('Material Consumption Records')

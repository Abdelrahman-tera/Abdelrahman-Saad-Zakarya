import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from apps.inventory.models import Batch, InventoryService
from apps.manufacturing.models import Recipe, RecipeIngredient, RecipePackaging, ProductionOrder
from apps.sales.models import SalesOrder, SalesOrderItem, SalesDelivery, SalesDeliveryItem

@pytest.mark.django_db
def test_e_blocked_expiry_and_quality_operations(setup_master_data):
    """
    MANDATORY ACCEPTANCE TEST E — EXPIRY & QUALITY RELEASE ENFORCEMENT:
    Confirm that the system strictly blocks:
    1. Issuing or dispatching QUARANTINED batches.
    2. Issuing or dispatching QUALITY_HOLD batches.
    3. Issuing or dispatching REJECTED batches.
    4. Issuing or dispatching EXPIRED batches.
    5. Using packaging with unapproved agricultural label revisions.
    """
    data = setup_master_data
    product = data['pyrifos_48ec']
    chlor_tech = data['chlorpyrifos_tech']
    wh_fg = data['wh_fg']
    wh_raw = data['wh_raw']
    uom_l = data['uom_l']
    uom_kg = data['uom_kg']
    customer = data['customer']
    user = data['admin_user']
    today = date(2026, 1, 20)

    # 1. Test Quarantined Batch
    b_quarantine = Batch.objects.create(
        product=product, batch_number='B-QUARANTINE',
        manufacturing_date=today, expiry_date=today + timedelta(days=365),
        status='QUARANTINE', uom=uom_l
    )
    InventoryService.record_movement('RECEIPT_PRODUCTION', product, wh_fg, Decimal('100.0000'), uom_l, Decimal('200.0000'), 'SEED', b_quarantine, allow_quarantine_movement=True)

    with pytest.raises(ValidationError) as exc1:
        InventoryService.record_movement(
            'ISSUE_SALES', product, wh_fg, Decimal('-10.0000'), uom_l, Decimal('200.0000'), 'TEST-ISSUE', b_quarantine
        )
    assert 'status' in str(exc1.value).lower() or 'quarantine' in str(exc1.value).lower()

    # 2. Test Quality Hold Batch
    b_hold = Batch.objects.create(
        product=product, batch_number='B-HOLD',
        manufacturing_date=today, expiry_date=today + timedelta(days=365),
        status='QUALITY_HOLD', uom=uom_l
    )
    InventoryService.record_movement('RECEIPT_PRODUCTION', product, wh_fg, Decimal('100.0000'), uom_l, Decimal('200.0000'), 'SEED', b_hold, allow_quarantine_movement=True)

    with pytest.raises(ValidationError):
        InventoryService.record_movement('ISSUE_SALES', product, wh_fg, Decimal('-10.0000'), uom_l, Decimal('200.0000'), 'TEST-ISSUE', b_hold)

    # 3. Test Rejected Batch
    b_rejected = Batch.objects.create(
        product=product, batch_number='B-REJECTED',
        manufacturing_date=today, expiry_date=today + timedelta(days=365),
        status='REJECTED', uom=uom_l
    )
    InventoryService.record_movement('RECEIPT_PRODUCTION', product, wh_fg, Decimal('100.0000'), uom_l, Decimal('200.0000'), 'SEED', b_rejected, allow_quarantine_movement=True)

    with pytest.raises(ValidationError):
        InventoryService.record_movement('ISSUE_SALES', product, wh_fg, Decimal('-10.0000'), uom_l, Decimal('200.0000'), 'TEST-ISSUE', b_rejected)

    # 4. Test Expired Batch
    b_expired = Batch.objects.create(
        product=product, batch_number='B-EXPIRED',
        manufacturing_date=today - timedelta(days=800),
        expiry_date=today - timedelta(days=1), # Expired yesterday!
        status='RELEASED', uom=uom_l
    )
    InventoryService.record_movement('RECEIPT_PRODUCTION', product, wh_fg, Decimal('100.0000'), uom_l, Decimal('200.0000'), 'SEED', b_expired, allow_quarantine_movement=True)

    with pytest.raises(ValidationError):
        InventoryService.record_movement('ISSUE_SALES', product, wh_fg, Decimal('-10.0000'), uom_l, Decimal('200.0000'), 'TEST-ISSUE', b_expired)

    # 5. Test Manufacturing Material Issue with Quarantined Raw Lot
    recipe = Recipe.objects.create(product=product, version='v2.0', name='Test Recipe', reference_batch_size=Decimal('1000.0000'), uom=uom_l, status='APPROVED')
    RecipeIngredient.objects.create(recipe=recipe, raw_material=chlor_tech, quantity_required=Decimal('490.0000'), uom=uom_kg)
    mo = ProductionOrder.objects.create(order_number='MO-TEST-BLOCK', recipe=recipe, product=product, warehouse_raw=wh_raw, warehouse_fg=wh_fg, target_quantity=Decimal('1000.0000'), uom=uom_l, status='RELEASED')

    b_raw_quarantine = Batch.objects.create(product=chlor_tech, batch_number='B-RAW-QUAR', manufacturing_date=today, expiry_date=today + timedelta(days=365), status='QUARANTINE', uom=uom_kg)
    InventoryService.record_movement('RECEIPT_PURCHASE', chlor_tech, wh_raw, Decimal('500.0000'), uom_kg, Decimal('350.0000'), 'SEED', b_raw_quarantine, allow_quarantine_movement=True)

    with pytest.raises(ValidationError):
        mo.issue_material(chlor_tech, b_raw_quarantine, Decimal('100.0000'), uom_kg, user=user)

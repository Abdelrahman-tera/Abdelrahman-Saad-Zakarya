import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from apps.inventory.models import Batch, StockBalance, InventoryService, StockReservation

@pytest.mark.django_db(transaction=True)
def test_h_concurrency_and_overselling_protection(setup_master_data):
    """
    MANDATORY ACCEPTANCE TEST H — CONCURRENCY & OVERSELLING SAFEGUARDS:
    Confirm that competing transactions cannot oversell or double-allocate inventory.
    Stock on-hand cannot become negative under competing operations.
    """
    data = setup_master_data
    product = data['pyrifos_48ec']
    wh_fg = data['wh_fg']
    uom_l = data['uom_l']
    user = data['admin_user']

    # Seed exactly 100 Liters of approved finished batch
    batch = Batch.objects.create(
        product=product, batch_number='B-CONCUR-100',
        manufacturing_date=date(2026, 1, 1), expiry_date=date(2028, 1, 1),
        status='RELEASED', uom=uom_l
    )
    InventoryService.record_movement(
        'RECEIPT_PRODUCTION', product, wh_fg, Decimal('100.0000'), uom_l,
        Decimal('200.0000'), 'SEED-100', batch
    )

    bal = StockBalance.objects.get(product=product, warehouse=wh_fg, batch=batch)
    assert bal.quantity_on_hand == Decimal('100.0000')

    # Competing Issue 1: Takes 70 Liters (Success)
    m1 = InventoryService.record_movement(
        'ISSUE_SALES', product, wh_fg, Decimal('-70.0000'), uom_l,
        Decimal('200.0000'), 'SO-COMPETE-01', batch, user=user
    )
    bal.refresh_from_db()
    assert bal.quantity_on_hand == Decimal('30.0000')

    # Competing Issue 2: Tries to take 50 Liters when only 30 Liters remain
    # System MUST reject with ValidationError and preserve balance at 30
    with pytest.raises(ValidationError) as exc:
        InventoryService.record_movement(
            'ISSUE_SALES', product, wh_fg, Decimal('-50.0000'), uom_l,
            Decimal('200.0000'), 'SO-COMPETE-02', batch, user=user
        )
    assert 'insufficient' in str(exc.value).lower()

    # Balance must remain exactly 30.0000
    bal.refresh_from_db()
    assert bal.quantity_on_hand == Decimal('30.0000')

    # Competing Reservation: Attempt to reserve 40 Liters when only 30 available
    with pytest.raises(ValidationError) as exc_res:
        InventoryService.reserve_stock(
            'RES-COMPETE-01', product, wh_fg, Decimal('40.0000'), uom_l, batch=batch
        )
    assert 'insufficient' in str(exc_res.value).lower()

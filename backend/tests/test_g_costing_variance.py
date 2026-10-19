import pytest
from decimal import Decimal
from datetime import date
from apps.manufacturing.models import Recipe, RecipeIngredient, ProductionOrder
from apps.inventory.models import Batch, InventoryService
from apps.costing.services import CostAccountingService

@pytest.mark.django_db
def test_g_costing_and_variance_analysis(setup_master_data):
    """
    MANDATORY ACCEPTANCE TEST G — COSTING & VARIANCE ANALYSIS:
    Change actual material usage and purchase prices from planned values.
    Verify that the system calculates and explains:
    1. Material Usage Variance (MUV)
    2. Material Price Variance (MPV)
    3. Total Net Variance reconciling with batch production cost.
    """
    data = setup_master_data
    product = data['pyrifos_48ec']
    chlor_tech = data['chlorpyrifos_tech'] # Standard cost = 350.0000 EGP/kg
    wh_raw = data['wh_raw']
    wh_fg = data['wh_fg']
    uom_kg = data['uom_kg']
    uom_l = data['uom_l']
    user = data['admin_user']

    # Step 1: Create Recipe (Planned: 490 kg Chlorpyrifos @ standard 350 EGP = 171,500 EGP)
    recipe = Recipe.objects.create(
        product=product, version='vCost1', name='Costing Test Recipe',
        reference_batch_size=Decimal('1000.0000'), uom=uom_l, status='APPROVED'
    )
    RecipeIngredient.objects.create(recipe=recipe, raw_material=chlor_tech, quantity_required=Decimal('490.0000'), uom=uom_kg)

    # Step 2: Production Order
    mo = ProductionOrder.objects.create(
        order_number='MO-COST-001',
        recipe=recipe,
        product=product,
        warehouse_raw=wh_raw,
        warehouse_fg=wh_fg,
        target_quantity=Decimal('1000.0000'),
        uom=uom_l,
        status='RELEASED'
    )

    # Step 3: Consume raw material lot with price variance (+20 EGP/kg) and usage variance (+20 kg)
    # Actual Price = 370 EGP/kg, Actual Quantity = 510 kg
    lot_cost = Batch.objects.create(
        product=chlor_tech, batch_number='LOT-COST-370',
        manufacturing_date=date(2026, 1, 1), expiry_date=date(2028, 1, 1),
        status='RELEASED', uom=uom_kg
    )
    # Stock lot with actual purchase price 370 EGP/kg
    InventoryService.record_movement(
        'RECEIPT_PURCHASE', chlor_tech, wh_raw, Decimal('600.0000'), uom_kg,
        Decimal('370.0000'), 'PO-EXPENSIVE', lot_cost
    )

    mo.issue_material(chlor_tech, lot_cost, Decimal('510.0000'), uom_kg, user=user)
    fg_batch = mo.complete_production(Decimal('1000.0000'), Decimal('0.0000'), 'BATCH-COST-FIN', user=user)

    # Step 4: Run Variance Analysis Engine
    variance_report = CostAccountingService.calculate_production_order_variance(mo)

    # Planned cost = 490 kg * 350 EGP/kg = 171,500.00 EGP
    assert Decimal(variance_report['total_planned_cost']) == Decimal('171500.00')
    # Actual cost = 510 kg * 370 EGP/kg = 188,700.00 EGP
    assert Decimal(variance_report['total_actual_cost']) == Decimal('188700.00')
    # Net variance = 188,700 - 171,500 = +17,200.00 EGP
    assert Decimal(variance_report['net_variance']) == Decimal('17200.00')

    # Material Usage Variance = (510 - 490) * 350 = 20 * 350 = 7,000.00 EGP (UNFAVORABLE)
    assert Decimal(variance_report['total_usage_variance']) == Decimal('7000.00')

    # Material Price Variance = (370 - 350) * 510 = 20 * 510 = 10,200.00 EGP (UNFAVORABLE)
    assert Decimal(variance_report['total_price_variance']) == Decimal('10200.00')

    # Reconcile sum of variances: 7,000 + 10,200 = 17,200
    assert (
        Decimal(variance_report['total_usage_variance']) + Decimal(variance_report['total_price_variance'])
    ) == Decimal(variance_report['net_variance'])

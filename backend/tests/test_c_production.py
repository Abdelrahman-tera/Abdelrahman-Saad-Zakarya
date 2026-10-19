import pytest
from decimal import Decimal
from datetime import date
from apps.manufacturing.models import (
    Recipe, RecipeIngredient, RecipePackaging, ProductionOrder, MaterialConsumption
)
from apps.inventory.models import Batch, StockBalance, InventoryService
from apps.quality.models import (
    QualitySpecification, QualityParameter, QualityInspection, QualityInspectionResult
)
from apps.accounting.models import JournalEntry

@pytest.mark.django_db
def test_c_production_workflow(setup_master_data):
    """
    MANDATORY ACCEPTANCE TEST C — PRODUCTION & CHEMICAL FORMULATION:
    Create production order from approved recipe -> reserve & consume raw materials ->
    record actual yield & scrap -> package output -> submit QC results ->
    release batch from quarantine -> calculate actual production cost.
    """
    data = setup_master_data
    pyrifos_product = data['pyrifos_48ec']
    chlor_tech = data['chlorpyrifos_tech']
    xylene = data['solvent_xylene']
    emulsifier = data['emulsifier_blend']
    bottle = data['bottle_1l']

    wh_raw = data['wh_raw']
    wh_fg = data['wh_fg']
    wh_pkg = data['wh_pkg']
    uom_kg = data['uom_kg']
    uom_l = data['uom_l']
    uom_btl = data['uom_bottle']
    user = data['admin_user']

    # Step 1: Create Approved Recipe & BOM
    recipe = Recipe.objects.create(
        product=pyrifos_product,
        version='v1.0',
        name='تركيبة بيريفوس 48% مركز قابل للاستحلاب القياسية',
        reference_batch_size=Decimal('1000.0000'),
        uom=uom_l,
        expected_yield_percent=Decimal('98.00'),
        loss_tolerance_percent=Decimal('2.50'),
        status='DRAFT'
    )
    # 490 kg Chlorpyrifos Tech 98%
    RecipeIngredient.objects.create(recipe=recipe, raw_material=chlor_tech, quantity_required=Decimal('490.0000'), uom=uom_kg, is_active_ingredient=True, sequence=1)
    # 530 kg Xylene Solvent
    RecipeIngredient.objects.create(recipe=recipe, raw_material=xylene, quantity_required=Decimal('530.0000'), uom=uom_kg, is_active_ingredient=False, sequence=2)
    # 100 kg Emulsifier Blend
    RecipeIngredient.objects.create(recipe=recipe, raw_material=emulsifier, quantity_required=Decimal('100.0000'), uom=uom_kg, is_active_ingredient=False, sequence=3)
    # Packaging requirement
    RecipePackaging.objects.create(recipe=recipe, packaging_material=bottle, quantity_required=Decimal('1000.0000'), uom=uom_btl, is_label_approved=True)

    recipe.approve(user=user)
    assert recipe.status == 'APPROVED'

    # Step 2: Seed Raw Material Stock (Released Batches)
    b_chlor = Batch.objects.create(product=chlor_tech, batch_number='LOT-CHLOR-001', manufacturing_date=date(2026, 1, 1), expiry_date=date(2028, 1, 1), status='RELEASED', uom=uom_kg)
    InventoryService.record_movement('RECEIPT_PURCHASE', chlor_tech, wh_raw, Decimal('1000.0000'), uom_kg, chlor_tech.standard_cost, 'SEED', b_chlor)

    b_xylene = Batch.objects.create(product=xylene, batch_number='LOT-XYL-001', manufacturing_date=date(2026, 1, 1), expiry_date=date(2028, 1, 1), status='RELEASED', uom=uom_kg)
    InventoryService.record_movement('RECEIPT_PURCHASE', xylene, wh_raw, Decimal('1500.0000'), uom_kg, xylene.standard_cost, 'SEED', b_xylene)

    b_emu = Batch.objects.create(product=emulsifier, batch_number='LOT-EMU-001', manufacturing_date=date(2026, 1, 1), expiry_date=date(2028, 1, 1), status='RELEASED', uom=uom_kg)
    InventoryService.record_movement('RECEIPT_PURCHASE', emulsifier, wh_raw, Decimal('500.0000'), uom_kg, emulsifier.standard_cost, 'SEED', b_emu)

    # Step 3: Create & Release Production Order
    mo = ProductionOrder.objects.create(
        order_number='MO-2026-001',
        recipe=recipe,
        product=pyrifos_product,
        warehouse_raw=wh_raw,
        warehouse_fg=wh_fg,
        target_quantity=Decimal('1000.0000'),
        uom=uom_l,
        status='DRAFT',
        created_by=user
    )
    mo.status = 'RELEASED'
    mo.save()

    # Step 4: Issue Raw Materials to WIP
    # 490 kg Chlorpyrifos @ 350 EGP = 171,500 EGP
    c1 = mo.issue_material(chlor_tech, b_chlor, Decimal('490.0000'), uom_kg, user=user)
    # 530 kg Xylene @ 60 EGP = 31,800 EGP
    c2 = mo.issue_material(xylene, b_xylene, Decimal('530.0000'), uom_kg, user=user)
    # 100 kg Emulsifier @ 180 EGP = 18,000 EGP
    c3 = mo.issue_material(emulsifier, b_emu, Decimal('100.0000'), uom_kg, user=user)

    expected_total_cost = Decimal('171500.00') + Decimal('31800.00') + Decimal('18000.00') # 221,300.00 EGP
    assert mo.total_actual_cost == expected_total_cost

    # Step 5: Complete Production Formulation
    # Actual output = 980 Liters, Scrap/Loss = 20 Liters
    fg_batch = mo.complete_production(
        actual_output=Decimal('980.0000'),
        scrap_qty=Decimal('20.0000'),
        batch_number='BATCH-PYRI-2026-001',
        mfg_date=date(2026, 1, 20),
        expiry_date=date(2028, 1, 20),
        user=user
    )

    # Crucial: Output batch MUST initially be in QUARANTINE!
    assert fg_batch.status == 'QUARANTINE'
    assert fg_batch.is_usable() is False

    # Step 6: Quality Control Inspection & Testing
    spec = QualitySpecification.objects.create(
        product=pyrifos_product,
        spec_type='FINISHED_PRODUCT',
        title='مواصفات الجودة المعتمدة لبيريفوس 48% EC'
    )
    param_assay = QualityParameter.objects.create(specification=spec, name='Active Ingredient Assay (Chlorpyrifos g/L)', min_value=Decimal('470.0000'), max_value=Decimal('490.0000'), unit_of_measure='g/L', is_critical=True, sequence=1)
    param_density = QualityParameter.objects.create(specification=spec, name='Density at 20°C', min_value=Decimal('1.1100'), max_value=Decimal('1.1300'), unit_of_measure='kg/L', is_critical=True, sequence=2)
    param_ph = QualityParameter.objects.create(specification=spec, name='pH (1% aqueous emulsion)', min_value=Decimal('5.5000'), max_value=Decimal('6.8000'), is_critical=True, sequence=3)

    qc_insp = QualityInspection.objects.create(
        inspection_number='QC-INSP-2026-001',
        specification=spec,
        product=pyrifos_product,
        batch=fg_batch,
        analyst=user
    )
    # Record Conforming Test Results
    QualityInspectionResult.objects.create(inspection=qc_insp, parameter=param_assay, observed_value_numeric=Decimal('482.0000'))
    QualityInspectionResult.objects.create(inspection=qc_insp, parameter=param_density, observed_value_numeric=Decimal('1.1180'))
    QualityInspectionResult.objects.create(inspection=qc_insp, parameter=param_ph, observed_value_numeric=Decimal('6.1000'))

    # Step 7: Release Batch & Issue Certificate of Analysis (COA)
    qc_insp.approve_and_release(user=user, coa_number='COA-PYRI-2026-001')
    assert qc_insp.status == 'APPROVED'

    # Batch is now officially RELEASED
    fg_batch.refresh_from_db()
    assert fg_batch.status == 'RELEASED'
    assert fg_batch.is_usable() is True

    # Step 8: Verify Actual Production Costing and FG Receipt Journal
    # Actual cost per Liter = 221,300 / 980 L = 225.8163 EGP/L
    fg_stock = StockBalance.objects.get(product=pyrifos_product, warehouse=wh_fg, batch=fg_batch)
    assert fg_stock.quantity_on_hand == Decimal('980.0000')

    fg_entry = JournalEntry.objects.get(entry_number='JRN-FG-MO-2026-001')
    assert fg_entry.status == 'POSTED'
    assert fg_entry.is_balanced()
    assert fg_entry.total_credit == expected_total_cost

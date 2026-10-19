import pytest
from decimal import Decimal
from datetime import date
from apps.traceability.services import TraceabilityService
from apps.inventory.models import Batch, InventoryService
from apps.manufacturing.models import Recipe, RecipeIngredient, ProductionOrder, MaterialConsumption
from apps.purchasing.models import PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem
from apps.sales.models import SalesOrder, SalesOrderItem, SalesDelivery, SalesDeliveryItem

@pytest.mark.django_db
def test_d_bidirectional_traceability(setup_master_data):
    """
    MANDATORY ACCEPTANCE TEST D — BIDIRECTIONAL BATCH GENEALOGY & TRACEABILITY:
    1. Forward: Start with raw lot -> identify all affected finished batches -> deliveries -> customers.
    2. Reverse: Start with finished batch -> identify raw lots -> suppliers -> GRNs.
    3. Recall Exposure: Verify exact quantities remaining in stock vs delivered to market.
    """
    data = setup_master_data
    supplier = data['supplier']
    customer = data['customer']
    raw_material = data['chlorpyrifos_tech']
    finished_prod = data['pyrifos_48ec']
    wh_raw = data['wh_raw']
    wh_fg = data['wh_fg']
    uom_kg = data['uom_kg']
    uom_l = data['uom_l']
    user = data['admin_user']

    # Step 1: Procurement of Raw Material Lot
    po = PurchaseOrder.objects.create(legal_entity=data['entity'], po_number='PO-TRACE-01', supplier=supplier, order_date=date(2026, 1, 1), status='APPROVED')
    po_item = PurchaseOrderItem.objects.create(purchase_order=po, product=raw_material, quantity_ordered=Decimal('500.0000'), uom=uom_kg, unit_price=Decimal('350.0000'))
    
    raw_batch = Batch.objects.create(
        product=raw_material,
        batch_number='LOT-RAW-CHLOR-77',
        supplier_lot_number='SUPP-LOT-SINO-77',
        manufacturing_date=date(2025, 11, 1),
        expiry_date=date(2027, 11, 1),
        status='RELEASED',
        uom=uom_kg
    )
    grn = GoodsReceipt.objects.create(grn_number='GRN-TRACE-01', purchase_order=po, warehouse=wh_raw, receipt_date=date(2026, 1, 2), status='POSTED')
    GoodsReceiptItem.objects.create(
        goods_receipt=grn, product=raw_material, quantity_received=Decimal('500.0000'),
        quantity_accepted=Decimal('500.0000'), uom=uom_kg, batch_number=raw_batch.batch_number,
        supplier_lot_number='SUPP-LOT-SINO-77'
    )
    InventoryService.record_movement('RECEIPT_PURCHASE', raw_material, wh_raw, Decimal('500.0000'), uom_kg, Decimal('350.0000'), 'GRN-TRACE-01', raw_batch)

    # Step 2: Formulation Production Order consuming raw_batch
    recipe = Recipe.objects.create(product=finished_prod, version='v1.0', name='Trace Recipe', reference_batch_size=Decimal('1000.0000'), uom=uom_l, status='APPROVED')
    RecipeIngredient.objects.create(recipe=recipe, raw_material=raw_material, quantity_required=Decimal('490.0000'), uom=uom_kg)

    mo = ProductionOrder.objects.create(order_number='MO-TRACE-01', recipe=recipe, product=finished_prod, warehouse_raw=wh_raw, warehouse_fg=wh_fg, target_quantity=Decimal('1000.0000'), uom=uom_l, status='RELEASED')
    mo.issue_material(raw_material, raw_batch, Decimal('490.0000'), uom_kg, user=user)

    fg_batch = mo.complete_production(Decimal('980.0000'), Decimal('20.0000'), 'BATCH-FIN-4401', user=user)
    fg_batch.status = 'RELEASED'
    fg_batch.save()

    # Step 3: Sales Delivery to Customer
    so = SalesOrder.objects.create(legal_entity=data['entity'], so_number='SO-TRACE-01', customer=customer, order_date=date(2026, 1, 10), status='CONFIRMED')
    SalesOrderItem.objects.create(sales_order=so, product=finished_prod, quantity_ordered=Decimal('300.0000'), uom=uom_l, unit_price=Decimal('320.0000'))
    delivery = SalesDelivery.objects.create(delivery_number='DEL-TRACE-01', sales_order=so, warehouse=wh_fg, delivery_date=date(2026, 1, 12), status='DRAFT')
    SalesDeliveryItem.objects.create(delivery=delivery, product=finished_prod, batch=fg_batch, quantity=Decimal('300.0000'), uom=uom_l)
    delivery.dispatch(user=user)

    # TEST D.1: Forward Traceability from Raw Lot
    forward_result = TraceabilityService.trace_forward_from_raw_lot(raw_batch)
    assert forward_result['source_raw_batch']['batch_number'] == 'LOT-RAW-CHLOR-77'
    assert forward_result['total_production_orders_count'] == 1
    assert forward_result['production_batches_produced'][0]['production_order_number'] == 'MO-TRACE-01'
    assert forward_result['production_batches_produced'][0]['finished_batch_number'] == 'BATCH-FIN-4401'
    assert forward_result['total_customers_affected_count'] == 1
    assert forward_result['affected_customer_deliveries'][0]['customer_code'] == customer.code
    assert forward_result['affected_customer_deliveries'][0]['quantity_dispatched'] == '300.0000'

    # TEST D.2: Reverse Traceability from Finished Batch
    reverse_result = TraceabilityService.trace_reverse_from_finished_batch(fg_batch)
    assert reverse_result['finished_batch']['batch_number'] == 'BATCH-FIN-4401'
    assert reverse_result['production_order_number'] == 'MO-TRACE-01'
    assert len(reverse_result['consumed_raw_materials']) == 1
    raw_info = reverse_result['consumed_raw_materials'][0]
    assert raw_info['batch_number'] == 'LOT-RAW-CHLOR-77'
    assert raw_info['supplier_origin']['supplier_code'] == supplier.code
    assert raw_info['supplier_origin']['grn_number'] == 'GRN-TRACE-01'

    # TEST D.3: Recall Exposure Calculation
    recall_result = TraceabilityService.calculate_recall_exposure(fg_batch)
    assert recall_result['batch_number'] == 'BATCH-FIN-4401'
    # Initial 980 L - 300 L delivered = 680 L remaining in FG warehouse
    assert Decimal(recall_result['total_remaining_in_warehouses']) == Decimal('680.0000')
    assert Decimal(recall_result['total_delivered_to_market']) == Decimal('300.0000')
    assert len(recall_result['affected_market_customers']) == 1
    assert recall_result['affected_market_customers'][0]['customer_code'] == customer.code

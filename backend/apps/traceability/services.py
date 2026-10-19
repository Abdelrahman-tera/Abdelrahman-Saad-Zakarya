from decimal import Decimal
from django.db.models import Sum
from apps.inventory.models import Batch, StockBalance, StockMovement
from apps.manufacturing.models import ProductionOrder, MaterialConsumption
from apps.sales.models import SalesDeliveryItem, SalesInvoice
from apps.purchasing.models import GoodsReceiptItem

class TraceabilityService:
    """Enterprise Agrochemical Batch Genealogy & Recall Exposure Analysis Engine."""

    @classmethod
    def trace_forward_from_raw_lot(cls, raw_batch: Batch) -> dict:
        """
        Forward Traceability:
        Raw Material Lot -> Production Orders -> Finished Formulated Batches -> Deliveries -> Customers.
        """
        consumptions = MaterialConsumption.objects.filter(batch=raw_batch).select_related(
            'production_order__product', 'production_order__created_batch'
        )

        production_records = []
        all_affected_finished_batches = set()
        all_affected_customers = []

        for c in consumptions:
            po = c.production_order
            fg_batch = po.created_batch
            if fg_batch:
                all_affected_finished_batches.add(fg_batch)

            production_records.append({
                'production_order_number': po.order_number,
                'formulation_product_code': po.product.code,
                'formulation_product_name': po.product.name_ar,
                'quantity_consumed': str(c.actual_quantity),
                'uom': c.uom.code,
                'finished_batch_number': fg_batch.batch_number if fg_batch else po.finished_batch_number,
                'manufacturing_date': str(fg_batch.manufacturing_date) if fg_batch else '',
                'expiry_date': str(fg_batch.expiry_date) if fg_batch else '',
                'fg_status': fg_batch.status if fg_batch else '',
            })

        # Find customer dispatches for all produced finished batches
        for fg_b in all_affected_finished_batches:
            delivery_items = SalesDeliveryItem.objects.filter(batch=fg_b).select_related(
                'delivery__sales_order__customer', 'delivery__warehouse'
            )
            for d_item in delivery_items:
                so = d_item.delivery.sales_order
                cust = so.customer
                all_affected_customers.append({
                    'finished_batch_number': fg_b.batch_number,
                    'delivery_number': d_item.delivery.delivery_number,
                    'delivery_date': str(d_item.delivery.delivery_date),
                    'sales_order_number': so.so_number,
                    'customer_code': cust.code,
                    'customer_name_ar': cust.name_ar,
                    'customer_name_en': cust.name_en,
                    'phone': cust.phone,
                    'territory': cust.territory,
                    'quantity_dispatched': str(d_item.quantity),
                    'uom': d_item.uom.code,
                })

        return {
            'source_raw_batch': {
                'batch_number': raw_batch.batch_number,
                'product_code': raw_batch.product.code,
                'product_name': raw_batch.product.name_ar,
                'supplier_lot_number': raw_batch.supplier_lot_number,
                'mfg_date': str(raw_batch.manufacturing_date),
                'expiry_date': str(raw_batch.expiry_date),
                'status': raw_batch.status,
            },
            'production_batches_produced': production_records,
            'affected_customer_deliveries': all_affected_customers,
            'total_production_orders_count': len(production_records),
            'total_customers_affected_count': len(all_affected_customers),
        }

    @classmethod
    def trace_reverse_from_finished_batch(cls, finished_batch: Batch) -> dict:
        """
        Reverse Traceability:
        Finished Product Batch -> Formulation MO -> Consumed Raw Lots -> Supplier POs & GRNs.
        """
        po = ProductionOrder.objects.filter(created_batch=finished_batch).first()
        ingredients_traced = []

        if po:
            consumptions = MaterialConsumption.objects.filter(production_order=po).select_related(
                'product', 'batch', 'uom'
            )
            for c in consumptions:
                raw_b = c.batch
                # Locate origin supplier GRN for this raw lot
                grn_item = GoodsReceiptItem.objects.filter(
                    product=raw_b.product, batch_number=raw_b.batch_number
                ).select_related('goods_receipt__purchase_order__supplier').first()

                supplier_info = {}
                if grn_item:
                    supp = grn_item.goods_receipt.purchase_order.supplier
                    supplier_info = {
                        'grn_number': grn_item.goods_receipt.grn_number,
                        'receipt_date': str(grn_item.goods_receipt.receipt_date),
                        'supplier_code': supp.code,
                        'supplier_name': supp.name_ar,
                        'supplier_lot': grn_item.supplier_lot_number,
                    }

                ingredients_traced.append({
                    'raw_material_code': c.product.code,
                    'raw_material_name': c.product.name_ar,
                    'batch_number': raw_b.batch_number,
                    'quantity_consumed': str(c.actual_quantity),
                    'uom': c.uom.code,
                    'supplier_origin': supplier_info
                })

        # Also get customers who received this finished batch
        deliveries = SalesDeliveryItem.objects.filter(batch=finished_batch).select_related(
            'delivery__sales_order__customer'
        )
        delivered_customers = [
            {
                'delivery_number': d.delivery.delivery_number,
                'delivery_date': str(d.delivery.delivery_date),
                'customer_code': d.delivery.sales_order.customer.code,
                'customer_name': d.delivery.sales_order.customer.name_ar,
                'quantity': str(d.quantity),
                'uom': d.uom.code,
            }
            for d in deliveries
        ]

        return {
            'finished_batch': {
                'batch_number': finished_batch.batch_number,
                'product_code': finished_batch.product.code,
                'product_name': finished_batch.product.name_ar,
                'mfg_date': str(finished_batch.manufacturing_date),
                'expiry_date': str(finished_batch.expiry_date),
                'status': finished_batch.status,
            },
            'production_order_number': po.order_number if po else 'N/A',
            'recipe_version': po.recipe.version if po else 'N/A',
            'consumed_raw_materials': ingredients_traced,
            'customer_dispatches': delivered_customers,
        }

    @classmethod
    def calculate_recall_exposure(cls, batch: Batch) -> dict:
        """
        Calculates complete recall metrics:
        - Remaining on-hand stock across warehouses to isolate/quarantine.
        - Quantity already dispatched to customers.
        - List of affected customers and contact details.
        """
        # 1. Remaining stock in warehouses
        balances = StockBalance.objects.filter(batch=batch).select_related('warehouse')
        remaining_stock = []
        total_remaining_qty = Decimal('0.0000')

        for b in balances:
            if b.quantity_on_hand > Decimal('0.0000'):
                remaining_stock.append({
                    'warehouse_code': b.warehouse.code,
                    'warehouse_name': b.warehouse.name_ar,
                    'quantity_on_hand': str(b.quantity_on_hand),
                    'quantity_reserved': str(b.quantity_reserved),
                })
                total_remaining_qty += b.quantity_on_hand

        # 2. Customer dispatches
        delivery_items = SalesDeliveryItem.objects.filter(batch=batch).select_related(
            'delivery__sales_order__customer'
        )
        total_delivered_qty = Decimal('0.0000')
        affected_customers = []

        for d in delivery_items:
            total_delivered_qty += d.quantity
            cust = d.delivery.sales_order.customer
            affected_customers.append({
                'customer_code': cust.code,
                'customer_name': cust.name_ar,
                'phone': cust.phone,
                'territory': cust.territory,
                'delivery_number': d.delivery.delivery_number,
                'delivery_date': str(d.delivery.delivery_date),
                'quantity': str(d.quantity),
            })

        return {
            'batch_number': batch.batch_number,
            'product_code': batch.product.code,
            'product_name': batch.product.name_ar,
            'initial_quantity': str(batch.initial_quantity),
            'total_remaining_in_warehouses': str(total_remaining_qty),
            'total_delivered_to_market': str(total_delivered_qty),
            'warehouse_hold_locations': remaining_stock,
            'affected_market_customers': affected_customers,
            'urgency_level': 'HIGH' if total_delivered_qty > Decimal('0.0000') else 'CONTAINED_INTERNALLY'
        }

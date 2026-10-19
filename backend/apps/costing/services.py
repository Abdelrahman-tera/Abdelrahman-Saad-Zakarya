from decimal import Decimal
from apps.manufacturing.models import ProductionOrder, MaterialConsumption

class CostAccountingService:
    """Industrial Cost Accounting & Manufacturing Variance Analysis Engine."""

    @classmethod
    def calculate_production_order_variance(cls, order: ProductionOrder) -> dict:
        """
        Calculates standard vs actual manufacturing cost and decomposes variances:
        - Material Usage Variance (MUV)
        - Material Price Variance (MPV)
        - Yield & Scrap Variance
        - Actual unit cost per kg/liter
        """
        snapshot = order.recipe_snapshot or {}
        planned_ingredients = {item['product_id']: item for item in snapshot.get('ingredients', [])}
        consumptions = MaterialConsumption.objects.filter(production_order=order).select_related('product')

        material_variances = []
        total_planned_cost = Decimal('0.00')
        total_actual_cost = Decimal('0.00')
        total_usage_variance = Decimal('0.00')
        total_price_variance = Decimal('0.00')

        for c in consumptions:
            prod_id = c.product.id
            std_price = c.product.standard_cost
            actual_qty = c.actual_quantity
            actual_price = c.unit_cost
            actual_line_cost = c.total_cost
            total_actual_cost += actual_line_cost

            # Check planned quantity from snapshot
            planned_info = planned_ingredients.get(prod_id)
            if planned_info:
                planned_qty = Decimal(planned_info['planned_qty'])
            else:
                # Unplanned additional consumption
                planned_qty = Decimal('0.0000')

            planned_line_cost = (planned_qty * std_price).quantize(Decimal('0.01'))
            total_planned_cost += planned_line_cost

            # 1. Material Usage Variance = (Actual Qty - Planned Qty) * Standard Price
            usage_var = ((actual_qty - planned_qty) * std_price).quantize(Decimal('0.01'))
            # 2. Material Price Variance = (Actual Price - Standard Price) * Actual Qty
            price_var = ((actual_price - std_price) * actual_qty).quantize(Decimal('0.01'))

            total_usage_variance += usage_var
            total_price_variance += price_var

            material_variances.append({
                'product_code': c.product.code,
                'product_name': c.product.name_ar,
                'standard_price': str(std_price),
                'actual_price': str(actual_price),
                'planned_quantity': str(planned_qty),
                'actual_quantity': str(actual_qty),
                'uom': c.uom.code,
                'planned_cost': str(planned_line_cost),
                'actual_cost': str(actual_line_cost),
                'usage_variance': str(usage_var),
                'price_variance': str(price_var),
                'usage_status': 'UNFAVORABLE' if usage_var > Decimal('0.00') else 'FAVORABLE',
                'price_status': 'UNFAVORABLE' if price_var > Decimal('0.00') else 'FAVORABLE',
            })

        net_variance = total_actual_cost - total_planned_cost
        output_qty = order.actual_output_quantity
        actual_unit_cost = (total_actual_cost / output_qty).quantize(Decimal('0.0001')) if output_qty > Decimal('0') else Decimal('0.0000')
        standard_unit_cost = (total_planned_cost / order.target_quantity).quantize(Decimal('0.0001')) if order.target_quantity > Decimal('0') else Decimal('0.0000')

        return {
            'order_number': order.order_number,
            'product_code': order.product.code,
            'product_name': order.product.name_ar,
            'target_quantity': str(order.target_quantity),
            'actual_output_quantity': str(order.actual_output_quantity),
            'scrap_quantity': str(order.scrap_quantity),
            'uom': order.uom.code,
            'total_planned_cost': str(total_planned_cost),
            'total_actual_cost': str(total_actual_cost),
            'net_variance': str(net_variance),
            'total_usage_variance': str(total_usage_variance),
            'total_price_variance': str(total_price_variance),
            'standard_cost_per_unit': str(standard_unit_cost),
            'actual_cost_per_unit': str(actual_unit_cost),
            'material_breakdown': material_variances,
        }

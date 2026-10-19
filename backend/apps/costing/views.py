from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from apps.manufacturing.models import ProductionOrder
from .services import CostAccountingService

class ProductionOrderCostingView(APIView):
    """Calculates planned vs actual batch cost and variance decomposition."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = ProductionOrder.objects.get(id=order_id)
            data = CostAccountingService.calculate_production_order_variance(order)
            return Response(data)
        except ProductionOrder.DoesNotExist:
            return Response({'error': 'Production Order not found'}, status=status.HTTP_404_NOT_FOUND)

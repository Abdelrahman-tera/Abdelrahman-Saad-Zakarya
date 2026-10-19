from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Batch, StockBalance, StockMovement, StockReservation, InventoryService
from .serializers import (
    BatchSerializer, StockBalanceSerializer, StockMovementSerializer, StockReservationSerializer
)
from apps.core.models import Product, Warehouse, UnitOfMeasure

class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all().select_related('product', 'uom')
    serializer_class = BatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'status', 'expiry_date']
    search_fields = ['batch_number', 'supplier_lot_number', 'product__code', 'product__name_ar']
    ordering_fields = ['expiry_date', 'manufacturing_date', 'created_at']

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Authorised action to release batch from quarantine to active usable stock."""
        batch = self.get_object()
        batch.status = 'RELEASED'
        batch.qc_released_by = request.user
        batch.qc_released_at = timezone.now()
        batch.save()
        return Response(BatchSerializer(batch).data)

    @action(detail=True, methods=['post'])
    def hold(self, request, pk=None):
        """Action to put batch on quality hold."""
        batch = self.get_object()
        batch.status = 'QUALITY_HOLD'
        batch.save()
        return Response(BatchSerializer(batch).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Action to reject non-conforming batch."""
        batch = self.get_object()
        batch.status = 'REJECTED'
        batch.save()
        return Response(BatchSerializer(batch).data)


class StockBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockBalance.objects.all().select_related('product', 'warehouse', 'batch')
    serializer_class = StockBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'warehouse', 'batch__status']
    search_fields = ['product__code', 'product__name_ar', 'warehouse__code', 'batch__batch_number']
    ordering_fields = ['quantity_on_hand', 'product__code']


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.all().select_related('product', 'warehouse', 'batch', 'uom')
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'warehouse', 'movement_type', 'batch']
    search_fields = ['source_document', 'product__code', 'batch__batch_number']
    ordering_fields = ['timestamp']

    @action(detail=False, methods=['post'])
    def manual_adjustment(self, request):
        """Records an approved inventory adjustment (gain or loss)."""
        data = request.data
        try:
            product = Product.objects.get(id=data['product_id'])
            warehouse = Warehouse.objects.get(id=data['warehouse_id'])
            uom = UnitOfMeasure.objects.get(id=data.get('uom_id', product.default_uom_id))
            quantity = Decimal(str(data['quantity']))
            unit_cost = Decimal(str(data.get('unit_cost', product.standard_cost)))
            batch = Batch.objects.filter(id=data.get('batch_id')).first()

            movement_type = 'ADJUSTMENT_IN' if quantity > Decimal('0') else 'ADJUSTMENT_OUT'
            m = InventoryService.record_movement(
                movement_type=movement_type,
                product=product,
                warehouse=warehouse,
                quantity=quantity,
                uom=uom,
                unit_cost=unit_cost,
                source_document=data.get('source_document', 'ADJ-MANUAL'),
                batch=batch,
                user=request.user,
                notes=data.get('notes', 'Manual Stock Adjustment')
            )
            return Response(StockMovementSerializer(m).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StockReservationViewSet(viewsets.ModelViewSet):
    queryset = StockReservation.objects.all().select_related('product', 'warehouse', 'batch')
    serializer_class = StockReservationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['product', 'warehouse', 'status', 'source_document']
    search_fields = ['source_document', 'product__code']

from decimal import Decimal
from django.core.exceptions import ValidationError
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Recipe, RecipeIngredient, RecipePackaging, ProductionOrder, MaterialConsumption
from .serializers import (
    RecipeSerializer, RecipeIngredientSerializer, RecipePackagingSerializer,
    ProductionOrderSerializer, MaterialConsumptionSerializer
)
from apps.core.models import Product, UnitOfMeasure
from apps.inventory.models import Batch

class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().select_related('product', 'uom').prefetch_related('ingredients__raw_material', 'packaging_materials__packaging_material')
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['product', 'status']
    search_fields = ['name', 'version', 'product__code', 'product__name_ar']

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        recipe = self.get_object()
        try:
            recipe.approve(user=request.user)
            return Response(RecipeSerializer(recipe).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProductionOrderViewSet(viewsets.ModelViewSet):
    queryset = ProductionOrder.objects.all().select_related('recipe', 'product', 'warehouse_raw', 'warehouse_fg', 'uom').prefetch_related('material_consumptions__product', 'material_consumptions__batch')
    serializer_class = ProductionOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'status', 'warehouse_raw', 'warehouse_fg']
    search_fields = ['order_number', 'product__code', 'finished_batch_number']
    ordering_fields = ['created_at', 'target_quantity']

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        po = self.get_object()
        if po.status != 'DRAFT':
            return Response({'error': 'Only draft orders can be released.'}, status=status.HTTP_400_BAD_REQUEST)
        po.status = 'RELEASED'
        po.save()
        return Response(ProductionOrderSerializer(po).data)

    @action(detail=True, methods=['post'])
    def issue_material(self, request, pk=None):
        po = self.get_object()
        data = request.data
        try:
            raw_material = Product.objects.get(id=data['product_id'])
            batch = Batch.objects.get(id=data['batch_id'])
            qty = Decimal(str(data['quantity']))
            uom = UnitOfMeasure.objects.get(id=data.get('uom_id', raw_material.default_uom_id))

            consumption = po.issue_material(
                raw_material=raw_material,
                batch=batch,
                actual_quantity=qty,
                uom=uom,
                user=request.user
            )
            return Response(MaterialConsumptionSerializer(consumption).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        po = self.get_object()
        data = request.data
        try:
            actual_output = Decimal(str(data['actual_output_quantity']))
            scrap_qty = Decimal(str(data.get('scrap_quantity', '0.0000')))
            batch_num = data['batch_number']

            produced_batch = po.complete_production(
                actual_output=actual_output,
                scrap_qty=scrap_qty,
                batch_number=batch_num,
                user=request.user
            )
            return Response({
                'message': 'Production order completed. Output batch placed in QUARANTINE.',
                'order': ProductionOrderSerializer(po).data,
                'batch_id': produced_batch.id,
                'batch_number': produced_batch.batch_number,
                'status': produced_batch.status,
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

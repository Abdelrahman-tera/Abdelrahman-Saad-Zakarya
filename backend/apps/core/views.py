from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    LegalEntity, Branch, Warehouse, StorageLocation,
    UnitOfMeasure, Product, ProductUOMConversion, Partner, AuditLog
)
from .serializers import (
    LegalEntitySerializer, BranchSerializer, WarehouseSerializer, StorageLocationSerializer,
    UnitOfMeasureSerializer, ProductSerializer, ProductUOMConversionSerializer, PartnerSerializer, AuditLogSerializer
)

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action', 'model_name', 'object_id']
    search_fields = ['model_name', 'object_id', 'description']
    ordering_fields = ['timestamp']


class LegalEntityViewSet(viewsets.ModelViewSet):
    queryset = LegalEntity.objects.all()
    serializer_class = LegalEntitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['code', 'name_ar', 'name_en', 'tax_id']


class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['legal_entity', 'is_factory', 'is_active']
    search_fields = ['code', 'name_ar', 'name_en']


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['branch', 'warehouse_type', 'is_active']
    search_fields = ['code', 'name_ar', 'name_en']


class StorageLocationViewSet(viewsets.ModelViewSet):
    queryset = StorageLocation.objects.all()
    serializer_class = StorageLocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['warehouse', 'is_active']
    search_fields = ['code', 'name']


class UnitOfMeasureViewSet(viewsets.ModelViewSet):
    queryset = UnitOfMeasure.objects.all()
    serializer_class = UnitOfMeasureSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category']
    search_fields = ['code', 'name_ar', 'name_en']


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'regulatory_type', 'formulation_type', 'is_active']
    search_fields = ['code', 'name_ar', 'name_en', 'registration_number', 'active_ingredient_composition']
    ordering_fields = ['code', 'name_ar', 'standard_cost', 'created_at']


class ProductUOMConversionViewSet(viewsets.ModelViewSet):
    queryset = ProductUOMConversion.objects.all()
    serializer_class = ProductUOMConversionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['product', 'from_uom', 'to_uom']


class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['partner_type', 'customer_class', 'territory', 'is_active']
    search_fields = ['code', 'name_ar', 'name_en', 'tax_id', 'commercial_register', 'phone']
    ordering_fields = ['code', 'name_ar', 'credit_limit', 'created_at']

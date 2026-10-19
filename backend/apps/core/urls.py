from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LegalEntityViewSet, BranchViewSet, WarehouseViewSet, StorageLocationViewSet,
    UnitOfMeasureViewSet, ProductViewSet, ProductUOMConversionViewSet, PartnerViewSet, AuditLogViewSet
)

router = DefaultRouter()
router.register(r'entities', LegalEntityViewSet)
router.register(r'branches', BranchViewSet)
router.register(r'warehouses', WarehouseViewSet)
router.register(r'locations', StorageLocationViewSet)
router.register(r'uoms', UnitOfMeasureViewSet)
router.register(r'products', ProductViewSet)
router.register(r'conversions', ProductUOMConversionViewSet)
router.register(r'partners', PartnerViewSet)
router.register(r'audit-logs', AuditLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

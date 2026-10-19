from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PurchaseOrderViewSet, GoodsReceiptViewSet, SupplierInvoiceViewSet, SupplierPaymentViewSet

router = DefaultRouter()
router.register(r'orders', PurchaseOrderViewSet)
router.register(r'receipts', GoodsReceiptViewSet)
router.register(r'invoices', SupplierInvoiceViewSet)
router.register(r'payments', SupplierPaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SalesQuotationViewSet, SalesOrderViewSet, SalesDeliveryViewSet,
    SalesInvoiceViewSet, CustomerReceiptViewSet
)

router = DefaultRouter()
router.register(r'quotations', SalesQuotationViewSet)
router.register(r'orders', SalesOrderViewSet)
router.register(r'deliveries', SalesDeliveryViewSet)
router.register(r'invoices', SalesInvoiceViewSet)
router.register(r'receipts', CustomerReceiptViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

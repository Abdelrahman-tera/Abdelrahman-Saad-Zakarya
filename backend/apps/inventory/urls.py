from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BatchViewSet, StockBalanceViewSet, StockMovementViewSet, StockReservationViewSet

router = DefaultRouter()
router.register(r'batches', BatchViewSet)
router.register(r'balances', StockBalanceViewSet)
router.register(r'movements', StockMovementViewSet)
router.register(r'reservations', StockReservationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

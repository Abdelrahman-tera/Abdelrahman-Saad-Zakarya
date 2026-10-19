from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FiscalYearViewSet, FiscalPeriodViewSet, AccountViewSet,
    JournalEntryViewSet, BankCashAccountViewSet
)

router = DefaultRouter()
router.register(r'fiscal-years', FiscalYearViewSet)
router.register(r'fiscal-periods', FiscalPeriodViewSet)
router.register(r'accounts', AccountViewSet)
router.register(r'journal-entries', JournalEntryViewSet)
router.register(r'bank-cash', BankCashAccountViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

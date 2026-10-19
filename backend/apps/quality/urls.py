from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QualitySpecificationViewSet, QualityParameterViewSet, QualityInspectionViewSet

router = DefaultRouter()
router.register(r'specifications', QualitySpecificationViewSet)
router.register(r'parameters', QualityParameterViewSet)
router.register(r'inspections', QualityInspectionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

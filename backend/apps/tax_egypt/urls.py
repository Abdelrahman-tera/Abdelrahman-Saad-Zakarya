from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ETADocumentViewSet, ETATransmissionLogViewSet

router = DefaultRouter()
router.register(r'documents', ETADocumentViewSet)
router.register(r'logs', ETATransmissionLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

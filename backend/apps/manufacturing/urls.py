from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RecipeViewSet, ProductionOrderViewSet

router = DefaultRouter()
router.register(r'recipes', RecipeViewSet)
router.register(r'production-orders', ProductionOrderViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

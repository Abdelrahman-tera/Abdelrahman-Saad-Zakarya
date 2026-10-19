from django.urls import path
from .views import ProductionOrderCostingView

urlpatterns = [
    path('order/<int:order_id>/', ProductionOrderCostingView.as_view(), name='order_costing'),
]

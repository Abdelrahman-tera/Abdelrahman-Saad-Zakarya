from django.urls import path
from .views import ForwardTraceView, ReverseTraceView, RecallExposureView

urlpatterns = [
    path('forward/<int:batch_id>/', ForwardTraceView.as_view(), name='trace_forward'),
    path('reverse/<int:batch_id>/', ReverseTraceView.as_view(), name='trace_reverse'),
    path('recall-exposure/<int:batch_id>/', RecallExposureView.as_view(), name='recall_exposure'),
]

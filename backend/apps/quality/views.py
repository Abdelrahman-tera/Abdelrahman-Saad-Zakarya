from django.core.exceptions import ValidationError
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import QualitySpecification, QualityParameter, QualityInspection, QualityInspectionResult
from .serializers import (
    QualitySpecificationSerializer, QualityParameterSerializer,
    QualityInspectionSerializer, QualityInspectionResultSerializer
)

class QualitySpecificationViewSet(viewsets.ModelViewSet):
    queryset = QualitySpecification.objects.all().select_related('product').prefetch_related('parameters')
    serializer_class = QualitySpecificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['product', 'spec_type', 'is_active']
    search_fields = ['title', 'product__code', 'product__name_ar']


class QualityParameterViewSet(viewsets.ModelViewSet):
    queryset = QualityParameter.objects.all()
    serializer_class = QualityParameterSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['specification']


class QualityInspectionViewSet(viewsets.ModelViewSet):
    queryset = QualityInspection.objects.all().select_related('specification', 'product', 'batch').prefetch_related('results__parameter')
    serializer_class = QualityInspectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'status', 'batch']
    search_fields = ['inspection_number', 'batch__batch_number', 'coa_number']
    ordering_fields = ['inspection_date']

    @action(detail=True, methods=['post'])
    def record_result(self, request, pk=None):
        """Records an inspection parameter result."""
        inspection = self.get_object()
        data = request.data
        try:
            param = QualityParameter.objects.get(id=data['parameter_id'], specification=inspection.specification)
            numeric_val = data.get('observed_value_numeric')
            text_val = data.get('observed_value_text', '')

            result, _ = QualityInspectionResult.objects.update_or_create(
                inspection=inspection,
                parameter=param,
                defaults={
                    'observed_value_numeric': numeric_val,
                    'observed_value_text': text_val,
                    'notes': data.get('notes', ''),
                }
            )
            return Response(QualityInspectionResultSerializer(result).data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def approve_and_release(self, request, pk=None):
        inspection = self.get_object()
        coa_num = request.data.get('coa_number', '')
        try:
            inspection.approve_and_release(user=request.user, coa_number=coa_num)
            return Response(QualityInspectionSerializer(inspection).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        inspection = self.get_object()
        reason = request.data.get('reason', '')
        try:
            inspection.reject_batch(user=request.user, reason=reason)
            return Response(QualityInspectionSerializer(inspection).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

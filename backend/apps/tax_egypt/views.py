import uuid
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import ETADocument, ETATransmissionLog
from .serializers import ETADocumentSerializer, ETATransmissionLogSerializer
from .adapter import ETAIntegrationAdapter
from apps.sales.models import SalesInvoice

class ETADocumentViewSet(viewsets.ModelViewSet):
    queryset = ETADocument.objects.all().select_related('sales_invoice__customer', 'sales_invoice__sales_order')
    serializer_class = ETADocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'document_type']
    search_fields = ['eta_uuid', 'submission_id', 'sales_invoice__invoice_number']

    @action(detail=False, methods=['post'], url_path='submit-invoice')
    def submit_sales_invoice(self, request):
        """Prepares and submits a sales invoice to the Egyptian Tax Authority."""
        invoice_id = request.data.get('invoice_id')
        try:
            invoice = SalesInvoice.objects.get(id=invoice_id)
            if invoice.status != 'POSTED':
                return Response({'error': 'Only posted sales invoices can be submitted to ETA.'}, status=status.HTTP_400_BAD_REQUEST)

            # Get or create ETADocument
            eta_doc, created = ETADocument.objects.get_or_create(
                sales_invoice=invoice,
                defaults={
                    'eta_uuid': str(uuid.uuid4()).upper(),
                    'document_type': 'I',
                    'status': 'DRAFT'
                }
            )

            res = ETAIntegrationAdapter.submit_invoice(eta_doc)
            return Response(res, status=status.HTTP_200_OK)
        except SalesInvoice.DoesNotExist:
            return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ETATransmissionLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ETATransmissionLog.objects.all()
    serializer_class = ETATransmissionLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['eta_document', 'is_success']

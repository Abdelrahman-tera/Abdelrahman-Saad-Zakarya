from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    SalesQuotation, SalesOrder, SalesDelivery, SalesInvoice, CustomerReceipt
)
from .serializers import (
    SalesQuotationSerializer, SalesOrderSerializer,
    SalesDeliverySerializer, SalesInvoiceSerializer, CustomerReceiptSerializer
)

class SalesQuotationViewSet(viewsets.ModelViewSet):
    queryset = SalesQuotation.objects.all().select_related('customer', 'legal_entity').prefetch_related('items__product')
    serializer_class = SalesQuotationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['customer', 'status']
    search_fields = ['quotation_number', 'customer__name_ar']


class SalesOrderViewSet(viewsets.ModelViewSet):
    queryset = SalesOrder.objects.all().select_related('customer', 'legal_entity').prefetch_related('items__product')
    serializer_class = SalesOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'status', 'order_date']
    search_fields = ['so_number', 'customer__name_ar', 'customer__name_en']
    ordering_fields = ['order_date', 'total_amount']

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        so = self.get_object()
        try:
            so.confirm()
            return Response(SalesOrderSerializer(so).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def override_credit(self, request, pk=None):
        so = self.get_object()
        reason = request.data.get('reason', '')
        so.credit_override = True
        so.credit_override_by = request.user
        so.credit_override_reason = reason
        so.save()
        return Response(SalesOrderSerializer(so).data)


class SalesDeliveryViewSet(viewsets.ModelViewSet):
    queryset = SalesDelivery.objects.all().select_related('sales_order', 'warehouse').prefetch_related('items__product', 'items__batch')
    serializer_class = SalesDeliverySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['sales_order', 'warehouse', 'status']
    search_fields = ['delivery_number', 'sales_order__so_number']

    @action(detail=True, methods=['post'])
    def dispatch_goods(self, request, pk=None):
        delivery = self.get_object()
        try:
            delivery.dispatch(user=request.user)
            return Response(SalesDeliverySerializer(delivery).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SalesInvoiceViewSet(viewsets.ModelViewSet):
    queryset = SalesInvoice.objects.all().select_related('customer', 'sales_order', 'delivery')
    serializer_class = SalesInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['customer', 'status', 'invoice_date']
    search_fields = ['invoice_number', 'customer__name_ar']

    @action(detail=True, methods=['post'])
    def post_invoice(self, request, pk=None):
        inv = self.get_object()
        try:
            inv.post(user=request.user)
            return Response(SalesInvoiceSerializer(inv).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='reports/ar-aging')
    def ar_aging(self, request):
        """
        Generates the Accounts Receivable Aging Report with configurable intervals:
        Current (not overdue), 1-30 days, 31-60 days, 61-90 days, 90+ days overdue.
        """
        today = timezone.now().date()
        unpaid_invoices = SalesInvoice.objects.filter(status='POSTED')

        customer_aging = {}

        for inv in unpaid_invoices:
            due = inv.balance_due
            if due <= Decimal('0.00'):
                continue

            c_id = inv.customer.id
            if c_id not in customer_aging:
                customer_aging[c_id] = {
                    'customer_id': c_id,
                    'customer_code': inv.customer.code,
                    'customer_name': inv.customer.name_ar,
                    'credit_limit': str(inv.customer.credit_limit),
                    'current': Decimal('0.00'),
                    'days_1_30': Decimal('0.00'),
                    'days_31_60': Decimal('0.00'),
                    'days_61_90': Decimal('0.00'),
                    'over_90': Decimal('0.00'),
                    'total_outstanding': Decimal('0.00'),
                }

            days_overdue = (today - inv.due_date).days
            if days_overdue <= 0:
                customer_aging[c_id]['current'] += due
            elif 1 <= days_overdue <= 30:
                customer_aging[c_id]['days_1_30'] += due
            elif 31 <= days_overdue <= 60:
                customer_aging[c_id]['days_31_60'] += due
            elif 61 <= days_overdue <= 90:
                customer_aging[c_id]['days_61_90'] += due
            else:
                customer_aging[c_id]['over_90'] += due

            customer_aging[c_id]['total_outstanding'] += due

        # Format as list of stringified values
        result = []
        for c in customer_aging.values():
            result.append({
                'customer_id': c['customer_id'],
                'customer_code': c['customer_code'],
                'customer_name': c['customer_name'],
                'credit_limit': c['credit_limit'],
                'current': str(c['current']),
                'days_1_30': str(c['days_1_30']),
                'days_31_60': str(c['days_31_60']),
                'days_61_90': str(c['days_61_90']),
                'over_90': str(c['over_90']),
                'total_outstanding': str(c['total_outstanding']),
            })

        return Response(result)


class CustomerReceiptViewSet(viewsets.ModelViewSet):
    queryset = CustomerReceipt.objects.all().select_related('customer', 'sales_invoice', 'bank_cash_account')
    serializer_class = CustomerReceiptSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['customer', 'collection_date']
    search_fields = ['receipt_number', 'customer__name_ar', 'reference']

    @action(detail=True, methods=['post'])
    def post_receipt(self, request, pk=None):
        receipt = self.get_object()
        try:
            receipt.post(user=request.user)
            return Response(CustomerReceiptSerializer(receipt).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

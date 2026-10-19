from decimal import Decimal
from django.core.exceptions import ValidationError
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem, SupplierInvoice, SupplierPayment
from .serializers import (
    PurchaseOrderSerializer, PurchaseOrderItemSerializer,
    GoodsReceiptSerializer, GoodsReceiptItemSerializer,
    SupplierInvoiceSerializer, SupplierPaymentSerializer
)

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all().select_related('supplier', 'legal_entity').prefetch_related('items__product')
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['supplier', 'status', 'order_date']
    search_fields = ['po_number', 'supplier__name_ar', 'supplier__name_en']
    ordering_fields = ['order_date', 'total_amount']

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        po = self.get_object()
        po.status = 'APPROVED'
        po.approved_by = request.user
        po.save()
        return Response(PurchaseOrderSerializer(po).data)


class GoodsReceiptViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceipt.objects.all().select_related('purchase_order', 'warehouse').prefetch_related('items__product')
    serializer_class = GoodsReceiptSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['purchase_order', 'warehouse', 'status']
    search_fields = ['grn_number', 'purchase_order__po_number']

    @action(detail=True, methods=['post'])
    def post_grn(self, request, pk=None):
        grn = self.get_object()
        try:
            grn.post(user=request.user)
            return Response(GoodsReceiptSerializer(grn).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SupplierInvoiceViewSet(viewsets.ModelViewSet):
    queryset = SupplierInvoice.objects.all().select_related('supplier', 'purchase_order', 'goods_receipt')
    serializer_class = SupplierInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['supplier', 'status', 'invoice_date']
    search_fields = ['invoice_number', 'supplier__name_ar']

    @action(detail=True, methods=['post'])
    def post_invoice(self, request, pk=None):
        inv = self.get_object()
        try:
            inv.post(user=request.user)
            return Response(SupplierInvoiceSerializer(inv).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SupplierPaymentViewSet(viewsets.ModelViewSet):
    queryset = SupplierPayment.objects.all().select_related('supplier', 'supplier_invoice', 'bank_cash_account')
    serializer_class = SupplierPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['supplier', 'payment_date']
    search_fields = ['payment_number', 'supplier__name_ar', 'reference']

    @action(detail=True, methods=['post'])
    def post_payment(self, request, pk=None):
        payment = self.get_object()
        try:
            payment.post(user=request.user)
            return Response(SupplierPaymentSerializer(payment).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

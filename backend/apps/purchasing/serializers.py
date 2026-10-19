from rest_framework import serializers
from .models import PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem, SupplierInvoice, SupplierPayment

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_code = serializers.ReadOnlyField(source='product.code')
    product_name = serializers.ReadOnlyField(source='product.name_ar')
    uom_code = serializers.ReadOnlyField(source='uom.code')
    total_price = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    tax_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = '__all__'


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.ReadOnlyField(source='supplier.name_ar')

    class Meta:
        model = PurchaseOrder
        fields = '__all__'


class GoodsReceiptItemSerializer(serializers.ModelSerializer):
    product_code = serializers.ReadOnlyField(source='product.code')
    uom_code = serializers.ReadOnlyField(source='uom.code')

    class Meta:
        model = GoodsReceiptItem
        fields = '__all__'


class GoodsReceiptSerializer(serializers.ModelSerializer):
    items = GoodsReceiptItemSerializer(many=True, read_only=True)
    po_number = serializers.ReadOnlyField(source='purchase_order.po_number')
    warehouse_name = serializers.ReadOnlyField(source='warehouse.name_ar')

    class Meta:
        model = GoodsReceipt
        fields = '__all__'


class SupplierInvoiceSerializer(serializers.ModelSerializer):
    supplier_name = serializers.ReadOnlyField(source='supplier.name_ar')
    balance_due = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = SupplierInvoice
        fields = '__all__'


class SupplierPaymentSerializer(serializers.ModelSerializer):
    supplier_name = serializers.ReadOnlyField(source='supplier.name_ar')
    bank_name = serializers.ReadOnlyField(source='bank_cash_account.name_ar')

    class Meta:
        model = SupplierPayment
        fields = '__all__'

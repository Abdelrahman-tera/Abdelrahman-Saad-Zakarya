from rest_framework import serializers
from .models import (
    SalesQuotation, SalesQuotationItem, SalesOrder, SalesOrderItem,
    SalesDelivery, SalesDeliveryItem, SalesInvoice, CustomerReceipt
)

class SalesQuotationItemSerializer(serializers.ModelSerializer):
    product_code = serializers.ReadOnlyField(source='product.code')
    product_name = serializers.ReadOnlyField(source='product.name_ar')
    uom_code = serializers.ReadOnlyField(source='uom.code')
    line_subtotal = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    line_tax = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    line_total = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = SalesQuotationItem
        fields = '__all__'


class SalesQuotationSerializer(serializers.ModelSerializer):
    items = SalesQuotationItemSerializer(many=True, read_only=True)
    customer_name = serializers.ReadOnlyField(source='customer.name_ar')

    class Meta:
        model = SalesQuotation
        fields = '__all__'


class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_code = serializers.ReadOnlyField(source='product.code')
    product_name = serializers.ReadOnlyField(source='product.name_ar')
    uom_code = serializers.ReadOnlyField(source='uom.code')
    line_subtotal = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    line_tax = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    line_total = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = SalesOrderItem
        fields = '__all__'


class SalesOrderSerializer(serializers.ModelSerializer):
    items = SalesOrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.ReadOnlyField(source='customer.name_ar')

    class Meta:
        model = SalesOrder
        fields = '__all__'


class SalesDeliveryItemSerializer(serializers.ModelSerializer):
    product_code = serializers.ReadOnlyField(source='product.code')
    batch_number = serializers.ReadOnlyField(source='batch.batch_number')
    uom_code = serializers.ReadOnlyField(source='uom.code')

    class Meta:
        model = SalesDeliveryItem
        fields = '__all__'


class SalesDeliverySerializer(serializers.ModelSerializer):
    items = SalesDeliveryItemSerializer(many=True, read_only=True)
    so_number = serializers.ReadOnlyField(source='sales_order.so_number')
    warehouse_name = serializers.ReadOnlyField(source='warehouse.name_ar')

    class Meta:
        model = SalesDelivery
        fields = '__all__'


class SalesInvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.name_ar')
    balance_due = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = SalesInvoice
        fields = '__all__'


class CustomerReceiptSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.name_ar')
    bank_name = serializers.ReadOnlyField(source='bank_cash_account.name_ar')

    class Meta:
        model = CustomerReceipt
        fields = '__all__'

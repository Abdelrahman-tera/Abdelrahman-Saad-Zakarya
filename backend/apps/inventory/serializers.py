from rest_framework import serializers
from .models import Batch, StockBalance, StockMovement, StockReservation

class BatchSerializer(serializers.ModelSerializer):
    product_code = serializers.ReadOnlyField(source='product.code')
    product_name = serializers.ReadOnlyField(source='product.name_ar')
    uom_code = serializers.ReadOnlyField(source='uom.code')
    is_usable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Batch
        fields = '__all__'


class StockBalanceSerializer(serializers.ModelSerializer):
    product_code = serializers.ReadOnlyField(source='product.code')
    product_name = serializers.ReadOnlyField(source='product.name_ar')
    warehouse_code = serializers.ReadOnlyField(source='warehouse.code')
    warehouse_name = serializers.ReadOnlyField(source='warehouse.name_ar')
    batch_number = serializers.ReadOnlyField(source='batch.batch_number')
    expiry_date = serializers.ReadOnlyField(source='batch.expiry_date')
    quantity_available = serializers.DecimalField(max_digits=16, decimal_places=4, read_only=True)

    class Meta:
        model = StockBalance
        fields = '__all__'


class StockMovementSerializer(serializers.ModelSerializer):
    product_code = serializers.ReadOnlyField(source='product.code')
    warehouse_code = serializers.ReadOnlyField(source='warehouse.code')
    batch_number = serializers.ReadOnlyField(source='batch.batch_number')
    uom_code = serializers.ReadOnlyField(source='uom.code')

    class Meta:
        model = StockMovement
        fields = '__all__'


class StockReservationSerializer(serializers.ModelSerializer):
    product_code = serializers.ReadOnlyField(source='product.code')
    warehouse_code = serializers.ReadOnlyField(source='warehouse.code')

    class Meta:
        model = StockReservation
        fields = '__all__'

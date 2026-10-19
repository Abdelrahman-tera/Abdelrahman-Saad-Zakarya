from rest_framework import serializers
from .models import (
    LegalEntity, Branch, Warehouse, StorageLocation,
    UnitOfMeasure, Product, ProductUOMConversion, Partner, AuditLog
)

class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = AuditLog
        fields = '__all__'


class StorageLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageLocation
        fields = '__all__'


class WarehouseSerializer(serializers.ModelSerializer):
    locations = StorageLocationSerializer(many=True, read_only=True)
    branch_name = serializers.ReadOnlyField(source='branch.name_ar')

    class Meta:
        model = Warehouse
        fields = '__all__'


class BranchSerializer(serializers.ModelSerializer):
    warehouses = WarehouseSerializer(many=True, read_only=True)

    class Meta:
        model = Branch
        fields = '__all__'


class LegalEntitySerializer(serializers.ModelSerializer):
    branches = BranchSerializer(many=True, read_only=True)

    class Meta:
        model = LegalEntity
        fields = '__all__'


class UnitOfMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = '__all__'


class ProductUOMConversionSerializer(serializers.ModelSerializer):
    from_uom_code = serializers.ReadOnlyField(source='from_uom.code')
    to_uom_code = serializers.ReadOnlyField(source='to_uom.code')

    class Meta:
        model = ProductUOMConversion
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    default_uom_code = serializers.ReadOnlyField(source='default_uom.code')
    uom_conversions = ProductUOMConversionSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = '__all__'


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = '__all__'

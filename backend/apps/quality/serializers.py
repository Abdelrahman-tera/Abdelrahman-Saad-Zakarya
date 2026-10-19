from rest_framework import serializers
from .models import QualitySpecification, QualityParameter, QualityInspection, QualityInspectionResult

class QualityParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityParameter
        fields = '__all__'


class QualitySpecificationSerializer(serializers.ModelSerializer):
    parameters = QualityParameterSerializer(many=True, read_only=True)
    product_code = serializers.ReadOnlyField(source='product.code')
    product_name = serializers.ReadOnlyField(source='product.name_ar')

    class Meta:
        model = QualitySpecification
        fields = '__all__'


class QualityInspectionResultSerializer(serializers.ModelSerializer):
    parameter_name = serializers.ReadOnlyField(source='parameter.name')
    unit_of_measure = serializers.ReadOnlyField(source='parameter.unit_of_measure')
    min_value = serializers.ReadOnlyField(source='parameter.min_value')
    max_value = serializers.ReadOnlyField(source='parameter.max_value')

    class Meta:
        model = QualityInspectionResult
        fields = '__all__'


class QualityInspectionSerializer(serializers.ModelSerializer):
    results = QualityInspectionResultSerializer(many=True, read_only=True)
    product_code = serializers.ReadOnlyField(source='product.code')
    product_name = serializers.ReadOnlyField(source='product.name_ar')
    batch_number = serializers.ReadOnlyField(source='batch.batch_number')
    batch_status = serializers.ReadOnlyField(source='batch.status')

    class Meta:
        model = QualityInspection
        fields = '__all__'

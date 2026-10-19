from rest_framework import serializers
from .models import ETADocument, ETATransmissionLog

class ETATransmissionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ETATransmissionLog
        fields = '__all__'


class ETADocumentSerializer(serializers.ModelSerializer):
    transmission_logs = ETATransmissionLogSerializer(many=True, read_only=True)
    invoice_number = serializers.ReadOnlyField(source='sales_invoice.invoice_number')
    customer_name = serializers.ReadOnlyField(source='sales_invoice.customer.name_ar')

    class Meta:
        model = ETADocument
        fields = '__all__'

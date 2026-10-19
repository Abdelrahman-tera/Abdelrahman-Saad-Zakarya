from rest_framework import serializers
from .models import FiscalYear, FiscalPeriod, Account, JournalEntry, JournalItem, BankCashAccount

class FiscalPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiscalPeriod
        fields = '__all__'


class FiscalYearSerializer(serializers.ModelSerializer):
    periods = FiscalPeriodSerializer(many=True, read_only=True)

    class Meta:
        model = FiscalYear
        fields = '__all__'


class AccountSerializer(serializers.ModelSerializer):
    parent_code = serializers.ReadOnlyField(source='parent.code')
    children_count = serializers.IntegerField(source='children.count', read_only=True)

    class Meta:
        model = Account
        fields = '__all__'


class JournalItemSerializer(serializers.ModelSerializer):
    account_code = serializers.ReadOnlyField(source='account.code')
    account_name = serializers.ReadOnlyField(source='account.name_ar')
    partner_name = serializers.ReadOnlyField(source='partner.name_ar')

    class Meta:
        model = JournalItem
        fields = '__all__'


class JournalEntrySerializer(serializers.ModelSerializer):
    items = JournalItemSerializer(many=True, read_only=True)
    total_debit = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    total_credit = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    is_balanced = serializers.BooleanField(read_only=True)
    posted_by_name = serializers.ReadOnlyField(source='posted_by.username')

    class Meta:
        model = JournalEntry
        fields = '__all__'


class BankCashAccountSerializer(serializers.ModelSerializer):
    gl_account_code = serializers.ReadOnlyField(source='gl_account.code')

    class Meta:
        model = BankCashAccount
        fields = '__all__'

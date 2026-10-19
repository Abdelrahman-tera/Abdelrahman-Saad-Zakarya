from decimal import Decimal
from django.db.models import Sum, Q
from django.core.exceptions import ValidationError
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import FiscalYear, FiscalPeriod, Account, JournalEntry, JournalItem, BankCashAccount
from .serializers import (
    FiscalYearSerializer, FiscalPeriodSerializer, AccountSerializer,
    JournalEntrySerializer, JournalItemSerializer, BankCashAccountSerializer
)

class FiscalYearViewSet(viewsets.ModelViewSet):
    queryset = FiscalYear.objects.all()
    serializer_class = FiscalYearSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['legal_entity', 'is_closed']


class FiscalPeriodViewSet(viewsets.ModelViewSet):
    queryset = FiscalPeriod.objects.all()
    serializer_class = FiscalPeriodSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['fiscal_year', 'is_closed']


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account_type', 'is_reconcilable', 'is_active', 'parent']
    search_fields = ['code', 'name_ar', 'name_en']
    ordering_fields = ['code', 'name_ar']

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Calculates current posted debit, credit, and net balance for this account."""
        account = self.get_object()
        items = JournalItem.objects.filter(account=account, entry__status='POSTED')
        totals = items.aggregate(total_debit=Sum('debit'), total_credit=Sum('credit'))
        debit = totals['total_debit'] or Decimal('0.00')
        credit = totals['total_credit'] or Decimal('0.00')

        if account.account_type in ('ASSET', 'EXPENSE'):
            net = debit - credit
        else:
            net = credit - debit

        return Response({
            'account_id': account.id,
            'code': account.code,
            'name': account.name_ar,
            'type': account.account_type,
            'debit': str(debit),
            'credit': str(credit),
            'net_balance': str(net)
        })


class JournalEntryViewSet(viewsets.ModelViewSet):
    queryset = JournalEntry.objects.all().prefetch_related('items__account', 'items__partner')
    serializer_class = JournalEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['legal_entity', 'status', 'entry_date', 'fiscal_period']
    search_fields = ['entry_number', 'reference_document', 'memo']
    ordering_fields = ['entry_date', 'entry_number', 'created_at']

    @action(detail=True, methods=['post'])
    def post_entry(self, request, pk=None):
        """Action to permanently post a draft journal entry."""
        entry = self.get_object()
        try:
            entry.post(user=request.user)
            return Response(JournalEntrySerializer(entry).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reverse_entry(self, request, pk=None):
        """Action to reverse a posted journal entry with a balancing mirror entry."""
        entry = self.get_object()
        memo = request.data.get('memo', '')
        try:
            reversal = entry.create_reversal(user=request.user, memo=memo)
            return Response({
                'message': 'Journal entry successfully reversed.',
                'original_entry': JournalEntrySerializer(entry).data,
                'reversal_entry': JournalEntrySerializer(reversal).data,
            })
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='reports/trial-balance')
    def trial_balance(self, request):
        """Generates the authoritative Trial Balance report across all active accounts."""
        legal_entity_id = request.query_params.get('legal_entity')
        qs = JournalItem.objects.filter(entry__status='POSTED')
        if legal_entity_id:
            qs = qs.filter(entry__legal_entity_id=legal_entity_id)

        accounts = Account.objects.all().order_by('code')
        report_data = []
        total_period_debit = Decimal('0.00')
        total_period_credit = Decimal('0.00')

        for acc in accounts:
            acc_items = qs.filter(account=acc)
            totals = acc_items.aggregate(d=Sum('debit'), c=Sum('credit'))
            d = totals['d'] or Decimal('0.00')
            c = totals['c'] or Decimal('0.00')
            if d > Decimal('0.00') or c > Decimal('0.00'):
                report_data.append({
                    'account_code': acc.code,
                    'account_name_ar': acc.name_ar,
                    'account_name_en': acc.name_en,
                    'account_type': acc.account_type,
                    'debit': str(d),
                    'credit': str(c),
                })
                total_period_debit += d
                total_period_credit += c

        return Response({
            'trial_balance': report_data,
            'total_debit': str(total_period_debit),
            'total_credit': str(total_period_credit),
            'is_balanced': total_period_debit == total_period_credit
        })

    @action(detail=False, methods=['get'], url_path='reports/profit-loss')
    def profit_and_loss(self, request):
        """Generates the official Income Statement / Profit & Loss report."""
        qs = JournalItem.objects.filter(entry__status='POSTED')
        revenue_items = qs.filter(account__account_type='REVENUE')
        expense_items = qs.filter(account__account_type='EXPENSE')

        rev_totals = revenue_items.aggregate(d=Sum('debit'), c=Sum('credit'))
        total_revenue = (rev_totals['c'] or Decimal('0.00')) - (rev_totals['d'] or Decimal('0.00'))

        exp_totals = expense_items.aggregate(d=Sum('debit'), c=Sum('credit'))
        total_expense = (exp_totals['d'] or Decimal('0.00')) - (exp_totals['c'] or Decimal('0.00'))

        net_profit = total_revenue - total_expense

        return Response({
            'total_revenue': str(total_revenue),
            'total_expense': str(total_expense),
            'net_profit': str(net_profit),
            'currency': 'EGP'
        })


class BankCashAccountViewSet(viewsets.ModelViewSet):
    queryset = BankCashAccount.objects.all()
    serializer_class = BankCashAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['legal_entity', 'account_type', 'is_active']
    search_fields = ['code', 'name_ar', 'name_en', 'bank_name', 'account_number']

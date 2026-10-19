import pytest
from decimal import Decimal
from datetime import date
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.accounting.models import Account, JournalEntry, JournalItem, FiscalYear, FiscalPeriod

@pytest.mark.django_db
def test_f_accounting_integrity(setup_master_data):
    """
    MANDATORY ACCEPTANCE TEST F — ACCOUNTING INTEGRITY & IDEMPOTENCY:
    1. Verify that every posted journal balances. Unbalanced journals are rejected.
    2. Repeated submission / duplicate posting is prevented by idempotency keys.
    3. Unauthorized modification or deletion of posted journal items is strictly rejected.
    4. Controlled reversal produces balanced offsetting journal.
    5. Posting into a closed accounting period is rejected.
    """
    data = setup_master_data
    entity = data['entity']
    acc_bank = Account.objects.get(code='1001')
    acc_ar = Account.objects.get(code='1101')
    user = data['admin_user']
    period = data['period_1']

    # TEST F.1: Unbalanced journal rejection
    entry_unbalanced = JournalEntry.objects.create(
        legal_entity=entity, entry_number='JRN-TEST-UNBAL',
        entry_date=date(2026, 1, 15), fiscal_period=period, status='DRAFT'
    )
    JournalItem.objects.create(entry=entry_unbalanced, account=acc_bank, debit=Decimal('1000.00'), credit=Decimal('0.00'))
    JournalItem.objects.create(entry=entry_unbalanced, account=acc_ar, debit=Decimal('0.00'), credit=Decimal('800.00')) # Debit 1000 != Credit 800

    with pytest.raises(ValidationError) as exc:
        entry_unbalanced.post(user=user)
    assert 'not balanced' in str(exc.value)

    # TEST F.2: Balanced journal posts successfully
    entry_balanced = JournalEntry.objects.create(
        legal_entity=entity, entry_number='JRN-TEST-BAL',
        entry_date=date(2026, 1, 15), fiscal_period=period, status='DRAFT',
        idempotency_key='IDEMP-TX-1001'
    )
    item1 = JournalItem.objects.create(entry=entry_balanced, account=acc_bank, debit=Decimal('1000.00'), credit=Decimal('0.00'))
    item2 = JournalItem.objects.create(entry=entry_balanced, account=acc_ar, debit=Decimal('0.00'), credit=Decimal('1000.00'))

    entry_balanced.post(user=user)
    assert entry_balanced.status == 'POSTED'
    assert entry_balanced.is_balanced()

    # TEST F.3: Posted items cannot be modified or deleted
    with pytest.raises(ValidationError):
        item1.debit = Decimal('1200.00')
        item1.save()

    with pytest.raises(ValidationError):
        item2.delete()

    # TEST F.4: Idempotency uniqueness safeguard
    from django.db import transaction
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            JournalEntry.objects.create(
                legal_entity=entity, entry_number='JRN-TEST-DUP',
                entry_date=date(2026, 1, 15), status='DRAFT',
                idempotency_key='IDEMP-TX-1001' # Duplicate key!
            )

    # TEST F.5: Controlled Reversal
    rev_entry = entry_balanced.create_reversal(user=user, memo='Testing audit reversal')
    assert rev_entry.status == 'POSTED'
    assert rev_entry.is_balanced()
    assert entry_balanced.status == 'REVERSED'
    # Verify mirror reversal amounts
    rev_bank = rev_entry.items.get(account=acc_bank)
    assert rev_bank.credit == Decimal('1000.00')
    rev_ar = rev_entry.items.get(account=acc_ar)
    assert rev_ar.debit == Decimal('1000.00')

    # Reversing again should be rejected
    with pytest.raises(ValidationError):
        entry_balanced.create_reversal(user=user)

    # TEST F.6: Closed Period Enforcement
    closed_fy = FiscalYear.objects.create(legal_entity=entity, name='FY 2025', start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), is_closed=True)
    closed_period = FiscalPeriod.objects.create(fiscal_year=closed_fy, period_number=12, name='Dec 2025', start_date=date(2025, 12, 1), end_date=date(2025, 12, 31), is_closed=True)

    entry_closed_period = JournalEntry.objects.create(
        legal_entity=entity, entry_number='JRN-TEST-CLOSED',
        entry_date=date(2025, 12, 15), fiscal_period=closed_period, status='DRAFT'
    )
    JournalItem.objects.create(entry=entry_closed_period, account=acc_bank, debit=Decimal('500.00'), credit=Decimal('0.00'))
    JournalItem.objects.create(entry=entry_closed_period, account=acc_ar, debit=Decimal('0.00'), credit=Decimal('500.00'))

    with pytest.raises(ValidationError) as exc_period:
        entry_closed_period.post(user=user)
    assert 'closed' in str(exc_period.value).lower()

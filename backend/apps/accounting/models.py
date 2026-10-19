from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from apps.core.models import LegalEntity, Partner

User = get_user_model()


class FiscalYear(models.Model):
    """Fiscal / Financial Year according to the Egyptian financial calendar."""
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.CASCADE, related_name='fiscal_years')
    name = models.CharField(max_length=50) # e.g. "FY 2026"
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']
        verbose_name = _('Fiscal Year')
        verbose_name_plural = _('Fiscal Years')

    def __str__(self):
        return f"{self.name} ({self.legal_entity.code})"


class FiscalPeriod(models.Model):
    """Monthly or quarterly accounting period within a fiscal year."""
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name='periods')
    period_number = models.PositiveSmallIntegerField() # 1 to 12
    name = models.CharField(max_length=50) # e.g. "January 2026"
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ['fiscal_year', 'period_number']
        unique_together = ('fiscal_year', 'period_number')
        verbose_name = _('Fiscal Period')
        verbose_name_plural = _('Fiscal Periods')

    def __str__(self):
        return f"{self.name} [{'Closed' if self.is_closed else 'Open'}]"


class Account(models.Model):
    """Hierarchical Chart of Accounts adhering to the Egyptian Uniform Accounting System."""
    ACCOUNT_TYPES = [
        ('ASSET', _('Assets (أصول)')),
        ('LIABILITY', _('Liabilities (التزامات)')),
        ('EQUITY', _('Equity (حقوق ملكية)')),
        ('REVENUE', _('Revenue (إيرادات)')),
        ('EXPENSE', _('Expense (مصروفات)')),
    ]
    code = models.CharField(max_length=50, unique=True)
    name_ar = models.CharField(max_length=255, verbose_name=_('Account Name (Arabic)'))
    name_en = models.CharField(max_length=255, verbose_name=_('Account Name (English)'))
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='children')
    is_reconcilable = models.BooleanField(default=False, help_text=_('For AR/AP and bank clearing reconciliation'))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        verbose_name = _('Account')
        verbose_name_plural = _('Chart of Accounts')

    def __str__(self):
        return f"{self.code} - {self.name_ar}"


class JournalEntry(models.Model):
    """Authoritative double-entry general ledger journal entry."""
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('POSTED', _('Posted')),
        ('REVERSED', _('Reversed')),
    ]
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.CASCADE, related_name='journal_entries')
    entry_number = models.CharField(max_length=50, unique=True)
    entry_date = models.DateField(db_index=True)
    fiscal_period = models.ForeignKey(FiscalPeriod, on_delete=models.PROTECT, related_name='journal_entries', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', db_index=True)

    reference_document = models.CharField(max_length=100, blank=True, default='', db_index=True,
                                          help_text=_('Originating document e.g. INV-2026-001, GRN-2026-042'))
    idempotency_key = models.CharField(max_length=120, blank=True, null=True, unique=True,
                                      help_text=_('Deterministic key preventing duplicate posting'))
    memo = models.TextField(blank=True, default='')

    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='posted_journals')
    posted_at = models.DateTimeField(null=True, blank=True)
    reversed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reversed_journals')
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversal_of = models.OneToOneField('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reversal_entry')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-entry_date', '-id']
        verbose_name = _('Journal Entry')
        verbose_name_plural = _('Journal Entries')

    def __str__(self):
        return f"{self.entry_number} [{self.get_status_display()}] - {self.entry_date}"

    @property
    def total_debit(self) -> Decimal:
        return sum((item.debit for item in self.items.all()), Decimal('0.00'))

    @property
    def total_credit(self) -> Decimal:
        return sum((item.credit for item in self.items.all()), Decimal('0.00'))

    def is_balanced(self) -> bool:
        return self.total_debit == self.total_credit and self.total_debit > Decimal('0.00')

    def post(self, user=None):
        """Validates balance and fiscal period before permanently posting."""
        if self.status != 'DRAFT':
            raise ValidationError(_('Only draft journal entries can be posted.'))

        # Check fiscal period status if defined
        if self.fiscal_period and self.fiscal_period.is_closed:
            raise ValidationError(_('Cannot post to a closed accounting period.'))

        items = list(self.items.all())
        if not items:
            raise ValidationError(_('Cannot post an empty journal entry.'))

        total_debit = sum((item.debit for item in items), Decimal('0.00'))
        total_credit = sum((item.credit for item in items), Decimal('0.00'))

        if total_debit != total_credit:
            raise ValidationError(
                _('Journal entry is not balanced: Total Debit (%(debit)s) != Total Credit (%(credit)s)') % {
                    'debit': total_debit, 'credit': total_credit
                }
            )

        if total_debit <= Decimal('0.00'):
            raise ValidationError(_('Journal entry total amount must be strictly greater than zero.'))

        from django.utils import timezone
        self.status = 'POSTED'
        self.posted_by = user
        self.posted_at = timezone.now()
        self.save()

    def create_reversal(self, user, memo: str = '') -> 'JournalEntry':
        """Creates an auditable reversal journal entry balancing out this entry."""
        if self.status != 'POSTED':
            raise ValidationError(_('Only posted journal entries can be reversed.'))
        if hasattr(self, 'reversal_entry') and self.reversal_entry:
            raise ValidationError(_('This journal entry has already been reversed by %s.') % self.reversal_entry.entry_number)

        from django.utils import timezone
        with transaction.atomic():
            reversal_number = f"REV-{self.entry_number}"
            reversal_entry = JournalEntry.objects.create(
                legal_entity=self.legal_entity,
                entry_number=reversal_number,
                entry_date=timezone.now().date(),
                fiscal_period=self.fiscal_period,
                status='DRAFT',
                reference_document=f"Reversal of {self.entry_number}",
                memo=memo or f"Automatic reversal of {self.entry_number}",
                reversal_of=self,
            )

            for item in self.items.all():
                # Swap debit and credit to balance out
                JournalItem.objects.create(
                    entry=reversal_entry,
                    account=item.account,
                    partner=item.partner,
                    debit=item.credit,
                    credit=item.debit,
                    memo=f"Reversal: {item.memo}",
                )

            reversal_entry.post(user=user)
            self.status = 'REVERSED'
            self.reversed_by = user
            self.reversed_at = timezone.now()
            self.save()

            return reversal_entry


class JournalItem(models.Model):
    """Individual debit/credit line of a double-entry journal."""
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='items')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='journal_items')
    partner = models.ForeignKey(Partner, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='journal_items',
                                help_text=_('Subledger partner for Accounts Receivable / Accounts Payable'))
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'))
    memo = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        verbose_name = _('Journal Item')
        verbose_name_plural = _('Journal Items')

    def clean(self):
        if self.debit < Decimal('0.00') or self.credit < Decimal('0.00'):
            raise ValidationError(_('Debit and Credit amounts cannot be negative.'))
        if self.debit > Decimal('0.00') and self.credit > Decimal('0.00'):
            raise ValidationError(_('A single journal line cannot have both Debit and Credit amounts.'))
        if self.debit == Decimal('0.00') and self.credit == Decimal('0.00'):
            raise ValidationError(_('Journal line must have either a Debit or a Credit amount.'))
        if self.entry.status in ('POSTED', 'REVERSED'):
            raise ValidationError(_('Cannot add, modify or delete items from a posted or reversed journal entry.'))

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.entry.status in ('POSTED', 'REVERSED'):
            raise ValidationError(_('Cannot delete lines from a posted or reversed journal entry.'))
        super().delete(*args, **kwargs)


class BankCashAccount(models.Model):
    """Company bank account or physical cash treasury (خزينة نقدية)."""
    ACCOUNT_TYPE = [
        ('BANK', _('Bank Account (حساب بنكي)')),
        ('CASH_DESK', _('Cash Desk / Treasury (خزينة نقدية)')),
        ('PETTY_CASH', _('Petty Cash Custody (عهدة نقدية)')),
    ]
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.CASCADE, related_name='bank_accounts')
    code = models.CharField(max_length=30, unique=True)
    name_ar = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE, default='BANK')
    gl_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='bank_cash_mappings')
    currency = models.CharField(max_length=10, default='EGP')
    bank_name = models.CharField(max_length=100, blank=True, default='')
    account_number = models.CharField(max_length=50, blank=True, default='')
    iban = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Bank / Cash Account')
        verbose_name_plural = _('Bank & Cash Accounts')

    def __str__(self):
        return f"{self.code} - {self.name_ar} ({self.currency})"

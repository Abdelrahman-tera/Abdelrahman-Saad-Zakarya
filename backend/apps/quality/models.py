import uuid
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.core.models import Product
from apps.inventory.models import Batch

User = get_user_model()


class QualitySpecification(models.Model):
    """Product-specific chemical and physical quality specifications."""
    SPEC_TYPES = [
        ('INCOMING_RAW', _('Incoming Raw Material / Solvent')),
        ('INCOMING_PACKAGING', _('Incoming Packaging Material')),
        ('IN_PROCESS', _('In-Process Formulation Sample')),
        ('FINISHED_PRODUCT', _('Finished Product Release')),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='quality_specs')
    spec_type = models.CharField(max_length=30, choices=SPEC_TYPES)
    title = models.CharField(max_length=255)
    version = models.CharField(max_length=20, default='v1.0')
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('product', 'spec_type', 'version')
        verbose_name = _('Quality Specification')
        verbose_name_plural = _('Quality Specifications')

    def __str__(self):
        return f"{self.product.code} - {self.title} ({self.get_spec_type_display()})"


class QualityParameter(models.Model):
    """Specific measurable parameter in a chemical quality spec."""
    PARAM_TYPES = [
        ('NUMERIC', _('Numeric Range')),
        ('TEXT', _('Descriptive / Visual')),
        ('PASS_FAIL', _('Pass / Fail')),
    ]
    specification = models.ForeignKey(QualitySpecification, on_delete=models.CASCADE, related_name='parameters')
    name = models.CharField(max_length=150, help_text=_('e.g. Active Ingredient Assay %, pH at 20°C, Density kg/L, Suspensibility %'))
    param_type = models.CharField(max_length=20, choices=PARAM_TYPES, default='NUMERIC')

    target_value = models.CharField(max_length=100, blank=True, default='')
    min_value = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    max_value = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    unit_of_measure = models.CharField(max_length=30, blank=True, default='', help_text=_('%, g/L, cP, pH'))
    is_critical = models.BooleanField(default=True)
    sequence = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['sequence']
        verbose_name = _('Quality Parameter')
        verbose_name_plural = _('Quality Parameters')

    def is_value_conforming(self, numeric_val: Decimal = None, text_val: str = '') -> bool:
        if self.param_type == 'NUMERIC' and numeric_val is not None:
            if self.min_value is not None and numeric_val < self.min_value:
                return False
            if self.max_value is not None and numeric_val > self.max_value:
                return False
            return True
        elif self.param_type == 'PASS_FAIL':
            return text_val.strip().lower() in ('pass', 'مقبول', 'مطابق', 'true', 'yes')
        return True


class QualityInspection(models.Model):
    """Inspection record for raw material or finished product batch."""
    STATUS_CHOICES = [
        ('PENDING', _('Pending Sampling / Testing')),
        ('IN_PROGRESS', _('Testing In Progress')),
        ('APPROVED', _('Approved & Released (مطابق للمواصفات)')),
        ('REJECTED', _('Rejected / Non-Conforming (مرفوض)')),
    ]
    inspection_number = models.CharField(max_length=50, unique=True)
    specification = models.ForeignKey(QualitySpecification, on_delete=models.PROTECT, related_name='inspections')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='quality_inspections')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='quality_inspections')

    sample_size = models.CharField(max_length=100, default='1 Litre / 500g')
    inspection_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    coa_number = models.CharField(max_length=100, blank=True, default='', help_text=_('Certificate of Analysis Serial'))
    analyst = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspections_analyzed')
    decision_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspections_decided')
    decision_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-inspection_date']
        verbose_name = _('Quality Inspection')
        verbose_name_plural = _('Quality Inspections')

    def __str__(self):
        return f"{self.inspection_number} - {self.batch.batch_number} [{self.get_status_display()}]"

    @transaction.atomic
    def approve_and_release(self, user, coa_number: str = ''):
        """
        Approves QC inspection:
        1. Confirms all critical parameters conform to specifications.
        2. Releases the batch: batch.status = 'RELEASED'.
        3. Generates Certificate of Analysis (COA).
        """
        if self.status in ('APPROVED', 'REJECTED'):
            raise ValidationError(_('This inspection has already been finalized.'))

        # Check parameter conformance
        for res in self.results.all():
            if res.parameter.is_critical and not res.is_conforming:
                raise ValidationError(_('Cannot approve inspection: Critical parameter %s is non-conforming.') % res.parameter.name)

        self.status = 'APPROVED'
        self.decision_by = user
        self.decision_at = timezone.now()
        self.coa_number = coa_number or f"COA-{self.batch.batch_number}"
        self.save()

        # Release Batch
        self.batch.status = 'RELEASED'
        self.batch.qc_released_by = user
        self.batch.qc_released_at = timezone.now()
        self.batch.save()

    @transaction.atomic
    def reject_batch(self, user, reason: str = ''):
        """Rejects the batch and marks it REJECTED, locking it against use or sale."""
        if self.status in ('APPROVED', 'REJECTED'):
            raise ValidationError(_('This inspection has already been finalized.'))

        self.status = 'REJECTED'
        self.decision_by = user
        self.decision_at = timezone.now()
        self.remarks = f"{self.remarks}\nRejection reason: {reason}".strip()
        self.save()

        self.batch.status = 'REJECTED'
        self.batch.save()


class QualityInspectionResult(models.Model):
    """Recorded observation for a quality parameter during batch inspection."""
    inspection = models.ForeignKey(QualityInspection, on_delete=models.CASCADE, related_name='results')
    parameter = models.ForeignKey(QualityParameter, on_delete=models.PROTECT, related_name='+')
    observed_value_numeric = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    observed_value_text = models.CharField(max_length=255, blank=True, default='')
    is_conforming = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        verbose_name = _('Inspection Result')
        verbose_name_plural = _('Inspection Results')

    def save(self, *args, **kwargs):
        self.is_conforming = self.parameter.is_value_conforming(
            numeric_val=self.observed_value_numeric,
            text_val=self.observed_value_text
        )
        super().save(*args, **kwargs)

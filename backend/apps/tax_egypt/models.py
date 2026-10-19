import uuid
import hashlib
import json
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.sales.models import SalesInvoice

class ETADocument(models.Model):
    """Authoritative Egyptian Tax Authority (ETA) E-Invoice Document."""
    STATUS_CHOICES = [
        ('DRAFT', _('Draft / Ready for Signing')),
        ('SUBMITTED', _('Submitted to ETA (قيد المعالجة)')),
        ('VALID', _('Valid / Accepted by ETA (صحيحة ومعتمدة)')),
        ('INVALID', _('Invalid / Validation Error (غير صحيحة)')),
        ('CANCELLED', _('Cancelled (ملغاة)')),
        ('REJECTED', _('Rejected by Buyer (مرفوضة من المشتري)')),
    ]
    DOCUMENT_TYPES = [
        ('I', _('Invoice (فاتورة ضريبية)')),
        ('C', _('Credit Note (إشعار دائن)')),
        ('D', _('Debit Note (إشعار مدين)')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sales_invoice = models.OneToOneField(SalesInvoice, on_delete=models.CASCADE, related_name='eta_document')
    eta_uuid = models.CharField(max_length=64, unique=True, db_index=True)
    submission_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    document_type = models.CharField(max_length=5, choices=DOCUMENT_TYPES, default='I')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', db_index=True)

    eta_long_id = models.CharField(max_length=120, blank=True, default='', help_text=_('Official ETA Portal Public URL / Long ID'))
    document_hash = models.CharField(max_length=64, blank=True, default='', help_text=_('SHA-256 canonical hash'))
    raw_payload = models.JSONField(blank=True, null=True)
    validation_results = models.JSONField(blank=True, null=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('ETA E-Invoice Document')
        verbose_name_plural = _('ETA E-Invoice Documents')

    def __str__(self):
        return f"ETA {self.get_document_type_display()} - {self.sales_invoice.invoice_number} [{self.get_status_display()}]"

    def build_canonical_payload(self) -> dict:
        """
        Builds ETA v1.0 compliant canonical JSON payload:
        Maps company tax ID, customer tax ID/National ID, activity code, invoice items, and tax totals (T1 VAT 14%, T4 WHT 1%).
        """
        inv = self.sales_invoice
        so = inv.sales_order
        company = so.legal_entity
        cust = inv.customer

        # Build lines
        lines = []
        for idx, item in enumerate(so.items.all(), 1):
            line_subtotal = float(item.line_subtotal)
            line_tax = float(item.line_tax)
            line_total = line_subtotal + line_tax
            lines.append({
                "description": f"{item.product.name_ar} ({item.product.code})",
                "itemType": "EGS", # Egyptian Goods and Services standard classification
                "itemCode": f"EG-{company.tax_id}-{item.product.code}",
                "unitType": item.uom.code,
                "quantity": float(item.quantity_ordered),
                "unitValue": {
                    "currencySold": "EGP",
                    "amountEGP": float(item.unit_price)
                },
                "salesTotal": float(item.quantity_ordered * item.unit_price),
                "total": line_total,
                "valueDifference": 0.00,
                "totalTaxableFees": 0.00,
                "netTotal": line_subtotal,
                "itemsDiscount": float(item.quantity_ordered * item.unit_price * (item.discount_percent / Decimal('100.0'))),
                "discount": {
                    "rate": float(item.discount_percent),
                    "amount": float(item.quantity_ordered * item.unit_price * (item.discount_percent / Decimal('100.0')))
                },
                "taxableItems": [
                    {
                        "taxType": "T1", # VAT
                        "amount": line_tax,
                        "subType": "V009", # General 14%
                        "rate": 14.0
                    }
                ]
            })

        payload = {
            "issuer": {
                "address": {
                    "branchID": "0",
                    "country": "EG",
                    "governorate": "Giza",
                    "regionCity": "6th of October Industrial Zone",
                    "streetName": company.address or "Industrial Area",
                    "buildingNumber": "1"
                },
                "type": "B", # Business
                "id": company.tax_id.replace('-', '').strip(),
                "name": company.name_ar
            },
            "receiver": {
                "address": {
                    "country": "EG",
                    "governorate": cust.territory or "Cairo",
                    "regionCity": cust.territory or "Cairo",
                    "streetName": cust.address or "Customer Street",
                    "buildingNumber": "1"
                },
                "type": "B" if cust.tax_id else "P", # B = Business, P = Natural Person
                "id": cust.tax_id.replace('-', '').strip() if cust.tax_id else (cust.national_id or "29901010100000"),
                "name": cust.name_ar
            },
            "documentType": self.document_type,
            "documentTypeVersion": "1.0",
            "dateTimeIssued": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "taxpayerActivityCode": "2012", # Chemical & Fertilizer Manufacturing
            "internalID": inv.invoice_number,
            "invoiceLines": lines,
            "totalDiscountAmount": 0.00,
            "totalSalesAmount": float(inv.subtotal),
            "netAmount": float(inv.subtotal),
            "taxTotals": [
                {
                    "taxType": "T1", # VAT 14%
                    "amount": float(inv.vat_amount)
                },
                {
                    "taxType": "T4", # Withholding Tax WHT 1%
                    "amount": float(inv.wht_amount)
                }
            ],
            "totalAmount": float(inv.total_amount),
            "extraDiscountAmount": 0.00,
            "totalItemsDiscountAmount": 0.00
        }

        # Compute SHA-256 canonical hash
        canon_str = json.dumps(payload, sort_keys=True)
        self.document_hash = hashlib.sha256(canon_str.encode('utf-8')).hexdigest()
        self.raw_payload = payload
        self.save(update_fields=['document_hash', 'raw_payload'])
        return payload


class ETATransmissionLog(models.Model):
    """Audit log of all HTTP transmissions and responses to/from ETA APIs."""
    eta_document = models.ForeignKey(ETADocument, on_delete=models.CASCADE, related_name='transmission_logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    endpoint = models.CharField(max_length=255)
    http_status = models.PositiveSmallIntegerField()
    request_headers = models.JSONField(blank=True, null=True)
    response_body = models.JSONField(blank=True, null=True)
    is_success = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('ETA Transmission Log')
        verbose_name_plural = _('ETA Transmission Logs')

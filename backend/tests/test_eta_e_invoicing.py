import pytest
from decimal import Decimal
from datetime import date
from apps.sales.models import SalesOrder, SalesOrderItem, SalesInvoice
from apps.tax_egypt.models import ETADocument
from apps.tax_egypt.adapter import ETAIntegrationAdapter

@pytest.mark.django_db
def test_eta_e_invoicing_integration(setup_master_data):
    """
    TEST EGYPTIAN TAX AUTHORITY (ETA) E-INVOICING INTEGRATION:
    1. Prepares canonical ETA JSON schema v1.0.
    2. Validates activity code 2012 (Chemical & Fertilizer Manufacturing).
    3. Calculates SHA-256 canonical hash.
    4. Submits invoice to ETA adapter.
    5. Confirms ETA Document status becomes VALID with submission ID and long URL.
    """
    data = setup_master_data
    customer = data['customer']
    product = data['pyrifos_48ec']
    uom_l = data['uom_l']
    entity = data['entity']

    # Step 1: Create Sales Order and Posted Sales Invoice
    so = SalesOrder.objects.create(
        legal_entity=entity,
        so_number='SO-ETA-001',
        customer=customer,
        order_date=date(2026, 1, 15),
        status='CONFIRMED'
    )
    so_item = SalesOrderItem.objects.create(
        sales_order=so,
        product=product,
        quantity_ordered=Decimal('100.0000'),
        uom=uom_l,
        unit_price=Decimal('320.0000'),
        tax_rate=Decimal('0.1400')
    )
    so.recalculate_totals()

    inv = SalesInvoice.objects.create(
        invoice_number='INV-ETA-001',
        sales_order=so,
        customer=customer,
        invoice_date=date(2026, 1, 16),
        due_date=date(2026, 2, 28),
        status='DRAFT',
        subtotal=Decimal('32000.00'),
        vat_amount=Decimal('4480.00'),
        wht_amount=Decimal('320.00'),
        total_amount=Decimal('36480.00')
    )
    inv.post()
    assert inv.status == 'POSTED'

    # Step 2: Create ETA Document
    eta_doc = ETADocument.objects.create(
        sales_invoice=inv,
        eta_uuid='UUID-ETA-TEST-001',
        document_type='I',
        status='DRAFT'
    )

    # Step 3: Build Canonical Payload & Compute Hash
    payload = eta_doc.build_canonical_payload()
    assert payload['issuer']['id'] == '100200300'
    assert payload['taxpayerActivityCode'] == '2012'
    assert payload['totalSalesAmount'] == 32000.00
    assert payload['totalAmount'] == 36480.00
    assert len(eta_doc.document_hash) == 64 # SHA-256 hex digest

    # Step 4: Submit to ETA Adapter
    result = ETAIntegrationAdapter.submit_invoice(eta_doc)
    assert result['status'] == 'VALID'
    assert result['eta_uuid'] == 'UUID-ETA-TEST-001'
    assert 'submission_id' in result

    eta_doc.refresh_from_db()
    assert eta_doc.status == 'VALID'
    assert eta_doc.transmission_logs.count() == 1
    assert eta_doc.transmission_logs.first().http_status == 202

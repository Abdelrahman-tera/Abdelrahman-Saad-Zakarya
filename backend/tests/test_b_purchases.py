import pytest
from decimal import Decimal
from datetime import date
from apps.purchasing.models import (
    PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem,
    SupplierInvoice, SupplierPayment
)
from apps.inventory.models import Batch, StockBalance
from apps.accounting.models import JournalEntry

@pytest.mark.django_db
def test_b_purchases_full_workflow(setup_master_data):
    """
    MANDATORY ACCEPTANCE TEST B — PURCHASING & 3-WAY MATCH WORKFLOW:
    Create PO -> partial receipt with accepted and rejected quantities ->
    post supplier invoice with 3-way match -> register partial payment ->
    reconcile stock, payables, and balanced accounting.
    """
    data = setup_master_data
    supplier = data['supplier']
    product = data['chlorpyrifos_tech']
    wh_raw = data['wh_raw']
    uom_kg = data['uom_kg']
    user = data['admin_user']
    bank_acc = data['bank_account']

    # Step 1: Create Purchase Order for 1000 kg @ 350 EGP/kg
    po = PurchaseOrder.objects.create(
        legal_entity=data['entity'],
        po_number='PO-2026-001',
        supplier=supplier,
        order_date=date(2026, 1, 5),
        status='DRAFT'
    )
    po_item = PurchaseOrderItem.objects.create(
        purchase_order=po,
        product=product,
        quantity_ordered=Decimal('1000.0000'),
        uom=uom_kg,
        unit_price=Decimal('350.0000'),
        tax_rate=Decimal('0.1400')
    )
    po.recalculate_totals()
    po.status = 'APPROVED'
    po.approved_by = user
    po.save()

    assert po.subtotal == Decimal('350000.00')
    assert po.tax_amount == Decimal('49000.00') # 14% VAT
    assert po.total_amount == Decimal('399000.00')

    # Step 2: Partial Delivery with Inspection (Received 600 kg: 550 Accepted, 50 Rejected)
    grn = GoodsReceipt.objects.create(
        grn_number='GRN-2026-001',
        purchase_order=po,
        warehouse=wh_raw,
        receipt_date=date(2026, 1, 10),
        status='DRAFT'
    )
    GoodsReceiptItem.objects.create(
        goods_receipt=grn,
        product=product,
        quantity_received=Decimal('600.0000'),
        quantity_accepted=Decimal('550.0000'),
        quantity_rejected=Decimal('50.0000'),
        uom=uom_kg,
        batch_number='BATCH-CHLOR-SUPP-01',
        supplier_lot_number='SINO-LOT-998',
        manufacturing_date=date(2025, 12, 1),
        expiry_date=date(2027, 12, 1)
    )

    grn.post(user=user)
    assert grn.status == 'POSTED'

    # Verify Batch created in QUARANTINE state
    batch = Batch.objects.get(product=product, batch_number='BATCH-CHLOR-SUPP-01')
    assert batch.status == 'QUARANTINE'
    assert batch.supplier_lot_number == 'SINO-LOT-998'

    # Verify Stock balance reflects accepted quantity
    stock_bal = StockBalance.objects.get(product=product, warehouse=wh_raw, batch=batch)
    assert stock_bal.quantity_on_hand == Decimal('550.0000')

    # Verify PO received status updated
    po_item.refresh_from_db()
    assert po_item.quantity_received == Decimal('550.0000')
    po.refresh_from_db()
    assert po.status == 'RECEIVED_PARTIAL'

    # Verify Goods Receipt Interim Clearing Journal
    grn_entry = JournalEntry.objects.get(reference_document='GRN-2026-001')
    assert grn_entry.status == 'POSTED'
    assert grn_entry.is_balanced()
    # 550 kg * 350 EGP/kg = 192,500.00 EGP
    assert grn_entry.total_debit == Decimal('192500.00')
    assert grn_entry.total_credit == Decimal('192500.00')

    # Step 3: Supplier Tax Invoice with 3-Way Match Verification
    # 550 kg * 350 = 192,500 Subtotal
    # VAT 14% = 26,950.00
    # WHT 1% (خصم منبع) = 1,925.00
    # Total invoice = 192,500 + 26,950 = 219,450.00
    # Net Supplier Payable = 219,450 - 1,925 = 217,525.00
    inv = SupplierInvoice.objects.create(
        invoice_number='SINV-2026-001',
        supplier=supplier,
        purchase_order=po,
        goods_receipt=grn,
        invoice_date=date(2026, 1, 12),
        due_date=date(2026, 2, 28),
        status='DRAFT',
        subtotal=Decimal('192500.00'),
        vat_amount=Decimal('26950.00'),
        wht_amount=Decimal('1925.00'),
        total_amount=Decimal('219450.00')
    )
    inv.post(user=user)
    assert inv.status == 'POSTED'

    # Verify Supplier Invoice Journal
    sinv_entry = JournalEntry.objects.get(reference_document='SINV-2026-001')
    assert sinv_entry.status == 'POSTED'
    assert sinv_entry.is_balanced()
    # Debits: 192,500 (interim AP clearing) + 26,950 (Input VAT) = 219,450.00
    assert sinv_entry.total_debit == Decimal('219450.00')
    assert sinv_entry.total_credit == Decimal('219450.00')

    # Step 4: Partial Payment Voucher to Supplier
    payment = SupplierPayment.objects.create(
        payment_number='PAY-2026-001',
        supplier=supplier,
        supplier_invoice=inv,
        bank_cash_account=bank_acc,
        payment_date=date(2026, 1, 15),
        amount=Decimal('100000.00'),
        reference='Cheque #445522'
    )
    payment.post(user=user)

    # Verify payment journal
    pay_entry = JournalEntry.objects.get(reference_document='PAY-2026-001')
    assert pay_entry.status == 'POSTED'
    assert pay_entry.is_balanced()
    assert pay_entry.total_debit == Decimal('100000.00')
    assert pay_entry.total_credit == Decimal('100000.00')

    # Verify remaining supplier invoice balance
    inv.refresh_from_db()
    assert inv.amount_paid == Decimal('100000.00')
    assert inv.balance_due == Decimal('119450.00')

import pytest
from decimal import Decimal
from datetime import date, timedelta
from apps.sales.models import (
    SalesQuotation, SalesQuotationItem, SalesOrder, SalesOrderItem,
    SalesDelivery, SalesDeliveryItem, SalesInvoice, CustomerReceipt
)
from apps.inventory.models import Batch, StockBalance, InventoryService, StockMovement
from apps.accounting.models import JournalEntry, JournalItem, Account

@pytest.mark.django_db
def test_a_sales_full_workflow(setup_master_data):
    """
    MANDATORY ACCEPTANCE TEST A — SALES WORKFLOW:
    Create quotation -> convert to sales order -> deliver stock -> post invoice ->
    receive partial payment -> confirm stock balance, receivable, revenue, tax treatment,
    cost of goods sold, and balanced journal entries.
    """
    data = setup_master_data
    customer = data['customer']
    product = data['pyrifos_48ec']
    wh_fg = data['wh_fg']
    uom_l = data['uom_l']
    user = data['admin_user']
    bank_acc = data['bank_account']

    # Step 1: Seed initial finished-goods batch and stock
    batch_fg = Batch.objects.create(
        product=product,
        batch_number='BATCH-FG-TESTA-001',
        manufacturing_date=date(2026, 1, 10),
        expiry_date=date(2028, 1, 10),
        status='RELEASED',
        initial_quantity=Decimal('500.0000'),
        uom=uom_l
    )
    InventoryService.record_movement(
        movement_type='RECEIPT_PRODUCTION',
        product=product,
        warehouse=wh_fg,
        quantity=Decimal('500.0000'),
        uom=uom_l,
        unit_cost=product.standard_cost, # 220 EGP/L
        source_document='INITIAL-PROD-BATCH',
        batch=batch_fg,
        user=user
    )

    initial_bal = StockBalance.objects.get(product=product, warehouse=wh_fg, batch=batch_fg)
    assert initial_bal.quantity_on_hand == Decimal('500.0000')

    # Step 2: Create Sales Quotation
    quote = SalesQuotation.objects.create(
        legal_entity=data['entity'],
        quotation_number='QT-2026-001',
        customer=customer,
        quotation_date=date(2026, 1, 15),
        expiry_date=date(2026, 2, 15),
        status='DRAFT'
    )
    q_item = SalesQuotationItem.objects.create(
        quotation=quote,
        product=product,
        quantity=Decimal('100.0000'),
        uom=uom_l,
        unit_price=Decimal('320.0000'),
        discount_percent=Decimal('0.00'),
        tax_rate=Decimal('0.1400')
    )
    quote.subtotal = q_item.line_subtotal # 32,000.00
    quote.tax_amount = q_item.line_tax   # 4,480.00 (14% VAT)
    quote.total_amount = quote.subtotal + quote.tax_amount # 36,480.00
    quote.status = 'ACCEPTED'
    quote.save()

    # Step 3: Convert Quotation to Confirmed Sales Order
    so = SalesOrder.objects.create(
        legal_entity=data['entity'],
        so_number='SO-2026-001',
        quotation=quote,
        customer=customer,
        order_date=date(2026, 1, 16),
        status='DRAFT'
    )
    so_item = SalesOrderItem.objects.create(
        sales_order=so,
        product=product,
        quantity_ordered=Decimal('100.0000'),
        uom=uom_l,
        unit_price=Decimal('320.0000'),
        discount_percent=Decimal('0.00'),
        tax_rate=Decimal('0.1400')
    )
    so.recalculate_totals()
    so.confirm()
    assert so.status == 'CONFIRMED'
    assert so.total_amount == Decimal('36480.00')

    # Step 4: Deliver Stock from Warehouse
    delivery = SalesDelivery.objects.create(
        delivery_number='DEL-2026-001',
        sales_order=so,
        warehouse=wh_fg,
        delivery_date=date(2026, 1, 17),
        status='DRAFT'
    )
    SalesDeliveryItem.objects.create(
        delivery=delivery,
        product=product,
        batch=batch_fg,
        quantity=Decimal('100.0000'),
        uom=uom_l
    )
    delivery.dispatch(user=user)
    assert delivery.status == 'DISPATCHED'

    # Verify Stock balance reduced atomically
    bal_after = StockBalance.objects.get(product=product, warehouse=wh_fg, batch=batch_fg)
    assert bal_after.quantity_on_hand == Decimal('400.0000')

    # Verify COGS Journal Entry generated and balanced
    cogs_entry = JournalEntry.objects.get(reference_document='DEL-2026-001')
    assert cogs_entry.status == 'POSTED'
    assert cogs_entry.is_balanced()
    # COGS = 100 L * 220 EGP/L = 22,000.00 EGP
    assert cogs_entry.total_debit == Decimal('22000.00')
    assert cogs_entry.total_credit == Decimal('22000.00')

    # Step 5: Post Sales Tax Invoice
    # Egyptian Tax: Subtotal = 32,000, VAT 14% = 4,480, WHT 1% = 320
    # Customer Net AR = 32,000 + 4,480 - 320 = 36,160 EGP
    inv = SalesInvoice.objects.create(
        invoice_number='INV-2026-001',
        sales_order=so,
        delivery=delivery,
        customer=customer,
        invoice_date=date(2026, 1, 18),
        due_date=date(2026, 2, 28),
        status='DRAFT',
        subtotal=Decimal('32000.00'),
        vat_amount=Decimal('4480.00'),
        wht_amount=Decimal('320.00'),
        total_amount=Decimal('36480.00')
    )
    inv.post(user=user)
    assert inv.status == 'POSTED'

    # Verify Invoice Journal Entry
    inv_entry = JournalEntry.objects.get(reference_document='INV-2026-001')
    assert inv_entry.status == 'POSTED'
    assert inv_entry.is_balanced()
    assert inv_entry.total_debit == Decimal('36480.00')
    assert inv_entry.total_credit == Decimal('36480.00')

    # Verify line accounts
    ar_line = inv_entry.items.get(account__code='1101')
    assert ar_line.debit == Decimal('36160.00') # Net after WHT
    wht_line = inv_entry.items.get(account__code='1105')
    assert wht_line.debit == Decimal('320.00') # 1% WHT asset
    rev_line = inv_entry.items.get(account__code='4101')
    assert rev_line.credit == Decimal('32000.00') # Revenue
    vat_line = inv_entry.items.get(account__code='2201')
    assert vat_line.credit == Decimal('4480.00') # 14% VAT liability

    # Step 6: Receive Partial Payment / Collection Voucher
    receipt = CustomerReceipt.objects.create(
        receipt_number='RCP-2026-001',
        customer=customer,
        sales_invoice=inv,
        bank_cash_account=bank_acc,
        collection_date=date(2026, 1, 20),
        amount=Decimal('20000.00'),
        reference='Bank Transfer NBE-TX-9988'
    )
    receipt.post(user=user)

    # Verify receipt journal entry
    rcp_entry = JournalEntry.objects.get(reference_document='RCP-2026-001')
    assert rcp_entry.status == 'POSTED'
    assert rcp_entry.is_balanced()
    assert rcp_entry.total_debit == Decimal('20000.00')
    assert rcp_entry.total_credit == Decimal('20000.00')

    # Verify remaining invoice balance due
    inv.refresh_from_db()
    assert inv.amount_collected == Decimal('20000.00')
    assert inv.balance_due == Decimal('16480.00')
    assert inv.status == 'POSTED' # Partially paid

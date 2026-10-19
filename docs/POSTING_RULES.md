# Accounting Posting Rule Matrix & Double-Entry Specifications

All operational and inventory transactions in the ERP trigger deterministic, balanced double-entry accounting records adhering to the Egyptian Uniform Accounting Standards.

---

## 1. Core Chart of Accounts Mapping

| Account Code | Account Name (Arabic) | Account Name (English) | Standard Nature | Account Type |
| :--- | :--- | :--- | :--- | :--- |
| **1001** | البنك الأهلي المصري - حساب جاري | NBE Bank Current Account | Debit | ASSET |
| **1002** | الخزينة النقدية الرئيسية | Main Cash Treasury | Debit | ASSET |
| **1101** | العملاء وأوراق القبض | Accounts Receivable (Customers) | Debit | ASSET |
| **1105** | ضريبة الخصم والإضافة المدينة (أ.ت.ص) | Withholding Tax Receivable (1%) | Debit | ASSET |
| **1201** | مخزون المواد الخام والمذيبات | Raw Materials & Solvent Inventory | Debit | ASSET |
| **1203** | إنتاج تحت التشغيل (WIP) | Work in Process (WIP) | Debit | ASSET |
| **1204** | مخزون الإنتاج التام | Finished Goods Inventory | Debit | ASSET |
| **1205** | ضريبة القيمة المضافة - مدخلات | Input VAT Recoverable (14%) | Debit | ASSET |
| **1209** | وسيط استلام البضائع والمواد | Goods Received Interim Clearing | Debit | ASSET |
| **2101** | الموردون وأوراق الدفع | Accounts Payable (Suppliers) | Credit | LIABILITY |
| **2106** | ضريبة الخصم والتحصيل الدائنة (منبع) | Withholding Tax Payable (1%) | Credit | LIABILITY |
| **2109** | وسيط فواتير الموردين غير المستلمة | Unbilled Supplier Accrual | Credit | LIABILITY |
| **2201** | ضريبة القيمة المضافة - مخرجات | Output VAT Payable (14%) | Credit | LIABILITY |
| **4101** | إيرادات مبيعات المبيدات والأسمدة | Agrochemical Sales Revenue | Credit | REVENUE |
| **5101** | تكلفة البضاعة المباعة (COGS) | Cost of Goods Sold (COGS) | Debit | EXPENSE |
| **5105** | انحراف وتوالف تصنيع كيميائي | Manufacturing Scrap Variance | Debit | EXPENSE |

---

## 2. Deterministic Posting Event Matrix

### A. Procurement & Inventory Receipts (Goods Receipt Note - GRN)
- **Debit**: `1209 - Goods Received Interim Clearing` (at PO purchase price)
- **Credit**: `2109 - Unbilled Supplier Accrual` (at PO purchase price)
- **Document Reference**: `GRN-{NUMBER}`
- **Idempotency Key**: `POST-GRN-{NUMBER}`

### B. Supplier Tax Invoice (Procure-to-Pay)
- **Debit**: `2109 - Unbilled Supplier Accrual` (Subtotal invoice amount)
- **Debit**: `1205 - Input VAT Recoverable` (14% Egyptian VAT)
- **Credit**: `2101 - Accounts Payable (Suppliers)` (Net amount payable after WHT)
- **Credit**: `2106 - Withholding Tax Payable` (1% WHT deducted by us for ETA)
- **Document Reference**: `SINV-{NUMBER}`

### C. Supplier Payment Voucher
- **Debit**: `2101 - Accounts Payable (Suppliers)` (Amount paid)
- **Credit**: `1001/1002 - Bank or Cash Treasury` (Amount paid)

### D. Manufacturing Material Issue to Reactor / Line
- **Debit**: `1203 - Work In Process (WIP)` (at Batch acquisition cost)
- **Credit**: `1201 - Raw Materials & Solvent Inventory` (at Batch acquisition cost)

### E. Finished Formulation Output & Scrap Clearance
- **Debit**: `1204 - Finished Goods Inventory` (Actual output quantity $\times$ Actual unit cost)
- **Debit**: `5105 - Manufacturing Scrap Variance` (Scrapped/evaporated residual value)
- **Credit**: `1203 - Work In Process (WIP)` (Total accumulated batch costs)

### F. Sales Delivery / Dispatch (Goods Issue)
- **Debit**: `5101 - Cost of Goods Sold (COGS)` (Dispatched quantity $\times$ Valuation unit cost)
- **Credit**: `1204 - Finished Goods Inventory` (Dispatched quantity $\times$ Valuation unit cost)
- **Document Reference**: `DEL-{NUMBER}`

### G. Customer Sales Tax Invoice (Order-to-Cash)
- **Debit**: `1101 - Accounts Receivable (Customers)` (Net invoice amount after WHT)
- **Debit**: `1105 - Withholding Tax Receivable` (1% deducted by customer)
- **Credit**: `4101 - Agrochemical Sales Revenue` (Subtotal before tax)
- **Credit**: `2201 - Output VAT Payable` (14% VAT collected for ETA)
- **Document Reference**: `INV-{NUMBER}`

### H. Customer Collection / Receipt Voucher
- **Debit**: `1001/1002 - Bank or Cash Treasury` (Amount collected)
- **Credit**: `1101 - Accounts Receivable (Customers)` (Amount collected)

---

## 3. Strict Audit & Immutability Rules
1. **Total Balance Check**: $\sum \text{Debit} = \sum \text{Credit}$. Unbalanced entries cannot be saved or posted.
2. **Immutability**: Once `status == 'POSTED'`, modifying, updating, or deleting journal lines raises a hard `ValidationError`.
3. **Controlled Reversal**: Corrections are made exclusively by posting an auditable mirror journal entry reversing debits and credits and updating the original entry status to `REVERSED`.
4. **Closed Periods**: Posting to closed fiscal years or periods is blocked by the database layer.

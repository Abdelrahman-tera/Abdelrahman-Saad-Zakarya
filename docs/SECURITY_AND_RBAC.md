# Security, Role-Based Access Control (RBAC) & Audit Specifications

This document defines user roles, permissions, record-level security, and audit trail enforcement for the Egyptian Agrochemical ERP.

---

## 1. Role-Based Access Control (RBAC) Matrix

| Role | Domain Access | Key Authorizations |
| :--- | :--- | :--- |
| **System Administrator** | All Domains | User provisioning, system configuration, backups, audit review |
| **Executive Manager** | Executive Dashboards & Reports | High-level KPI views, financial P&L, production summary, read-all |
| **Finance Manager** | Accounting, Costing, Sales, Purchases | Approves journal entries, reversals, credit limit overrides, period closing |
| **Accountant** | Accounting & Invoicing | Drafts journals, reconciles bank accounts, posts supplier/sales invoices |
| **Sales Manager** | Sales & Customers | Approves quotations, sales orders, customer discounts, monitors AR aging |
| **Sales Representative** | Sales & CRM | Creates quotations, registers customer orders, views assigned territory |
| **Collection Officer** | Receivables & Collections | Records customer collections, follow-ups on overdue aging intervals |
| **Purchasing Manager** | Procurement & Suppliers | Approves purchase orders, landed cost allocation, supplier contracts |
| **Warehouse Manager** | Inventory & Logistics | Authorizes internal transfers, physical stock counts, stock adjustments |
| **Storekeeper** | Warehouses | Executes goods receipts (GRN), issues materials, dispatches deliveries |
| **Production Manager** | Manufacturing & Formulations | Approves recipes and BOM revisions, releases production orders |
| **Production Supervisor**| Manufacturing Floor | Records actual chemical consumption, batch output, scrap and downtime |
| **Quality Manager** | QA / QC & Laboratories | Sets chemical specifications, authorizes batch release and Certificates of Analysis (COA) |
| **QC Analyst** | Laboratory Testing | Records observed parameter measurements, assay %, pH, density |
| **Internal Auditor** | Read-Only Across Ledgers | Full drill-down from financial reports to source perpetual movements |

---

## 2. Record-Level Security & Separation of Duties
- **Segregation of Procurement and Cash**: Storekeepers receiving materials cannot approve supplier invoices or issue payments.
- **Credit Exposure Control**: Sales representatives cannot confirm orders exceeding customer credit limits without explicit authorization from the Finance Manager recorded in `credit_override`.
- **Quality Quarantine Gate**: Storekeepers and sales managers cannot dispatch batches whose status is not `RELEASED`.

---

## 3. Cryptographic Security & Protections
- **Transport Security**: Enforced HTTPS with TLS 1.3, HSTS header, and secure cookies.
- **SQL Injection & XSS**: Django ORM parameterized queries, React automated DOM escaping.
- **CSRF Protection**: CSRF middleware and token rotation.
- **Secret Hygiene**: Strict isolation of database passwords, Django secret key, and ETA tax signing certificates via environment variables. Operational logs never contain passwords or tokens.

# Industrial ERP for Agrochemical & Fertilizer Manufacturing in Egypt
## نظام إدارة وتصنيع الكيماويات والمبيدات والأسمدة الزراعية

[![CI/CD Pipeline](https://github.com/company/agrochemical-erp/actions/workflows/ci.yml/badge.svg)](https://github.com/company/agrochemical-erp/actions)
[![License: Commercial](https://img.shields.io/badge/License-Proprietary%20%2F%20Commercial-blue.svg)](docs/THIRD_PARTY_LICENSES.md)
[![Python: 3.12 LTS](https://img.shields.io/badge/Python-3.12%20LTS-brightgreen.svg)](https://www.python.org/)
[![Django: 5.2 LTS](https://img.shields.io/badge/Django-5.2%20LTS-darkgreen.svg)](https://www.djangoproject.com/)
[![React: 19](https://img.shields.io/badge/React-19%20TypeScript-61dafb.svg)](https://react.dev/)
[![ETA: E-Invoicing v1.0](https://img.shields.io/badge/ETA%20E--Invoicing-v1.0%20Compliant-orange.svg)](docs/ETA_E_INVOICING.md)

---

## 1. Project Identity & Objective

This enterprise-grade, cloud-based ERP system is purpose-built for Egyptian industrial companies that manufacture, formulate, package, import, and distribute:
- **Agricultural Pesticides**: Insecticides, Fungicides, Herbicides, Acaricides, Nematocides (EC, SC, SL, WP, WG).
- **Chemical & Specialty Fertilizers**: Water-soluble NPKs, suspension fertilizers, micronutrients (EDDHA/EDTA chelates), biostimulants, and adjuvants.
- **Raw Materials & Packaging**: Technical active ingredients, industrial solvents, emulsifiers, co-ex barrier bottles, caps, and approved labels.

The system is designed with **Arabic as its primary language and native Right-to-Left (RTL) interface**, English as a secondary language, Egyptian Pound (EGP) as the base currency, Africa/Cairo timezone, and strict compliance with Egyptian Tax Authority (ETA) e-Invoicing regulations (Activity Code 2012).

---

## 2. Technical Stack & Architecture

- **Backend**: Python 3.12 LTS, Django 5.2 LTS, Django REST Framework, Modular Monolith architecture.
- **Database**: PostgreSQL 16/17/18 with ACID transactions, row-level concurrency locking (`select_for_update`), and exact decimal numeric types for financial and quantity arithmetic.
- **Background Processing & Caching**: Celery 5.6 + Redis 7.
- **Frontend**: React 19, TypeScript, Vite, Ant Design (with complete Arabic RTL support and dynamic English toggle).
- **Tax Integration**: Dedicated Egyptian Tax Authority (ETA) e-Invoicing & e-Receipt API adapter (canonical JSON, UUID, SHA-256 document hashing, 14% VAT, 1% WHT).
- **Containerization & CI/CD**: Docker, Docker Compose, Nginx reverse proxy, automated GitHub Actions pipeline.

```
/workspaces/Abdelrahman-Saad-Zakarya/
├── backend/
│   ├── config/              # Django settings, URLs, WSGI/ASGI, Celery
│   ├── apps/
│   │   ├── core/            # Legal entities, branches, warehouses, products, UOMs, audit
│   │   ├── accounting/      # General ledger, chart of accounts, journals, trial balance, P&L
│   │   ├── inventory/       # Perpetual stock ledger, batches, expiry, FEFO picking
│   │   ├── sales/           # Order-to-cash, credit checks, sales invoices, AR aging
│   │   ├── purchasing/      # Procure-to-pay, POs, GRN, 3-way match, supplier invoices
│   │   ├── manufacturing/   # Chemical formulations, BOMs, batch execution, scrap
│   │   ├── quality/         # Chemical QA/QC, test results, Certificate of Analysis (COA)
│   │   ├── traceability/    # Bidirectional genealogy & product recall engine
│   │   ├── costing/         # Industrial batch costing, material usage & price variances
│   │   └── tax_egypt/       # ETA e-invoicing adapter, serialization, validation
│   ├── tests/               # Full automated acceptance test suite (TEST A to J)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/             # Typed API client with error handling
│   │   ├── components/      # MainLayout with RTL / language toggle
│   │   ├── i18n/            # Arabic (ar-EG) & English (en-US) dictionaries
│   │   └── pages/           # Dashboard, Inventory, Manufacturing, Quality, Traceability, Accounting, Sales, ETA
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── nginx.conf
└── docs/                    # Architectural ERD, posting rules, deployment, ETA specifications
```

---

## 3. Quick Start & Local Execution

### Option A: Running with Docker Compose (Recommended for Production)

1. Clone repository and set up environment:
   ```bash
   cp .env.example .env
   docker compose build
   docker compose up -d
   ```

2. Run database migrations and seed demo data:
   ```bash
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py seed_demo_data
   ```

3. Access the application:
   - **Frontend UI (Arabic RTL)**: [http://localhost](http://localhost)
   - **Backend API Docs (Swagger UI)**: [http://localhost/api/docs/](http://localhost/api/docs/)
   - **ReDoc API Documentation**: [http://localhost/api/redoc/](http://localhost/api/redoc/)
   - **Django Admin**: [http://localhost/admin/](http://localhost/admin/) (Default credentials: `admin` / `AdminPass2026!`)

---

### Option B: Local Development Setup

1. **Backend Setup**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   python backend/manage.py migrate
   python backend/manage.py seed_demo_data
   python backend/manage.py runserver 0.0.0.0:8000
   ```

2. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open [http://localhost:5173](http://localhost:5173).

---

## 4. Running the Mandatory Acceptance Tests

The test suite validates every mandatory business scenario (TEST A through TEST J):

```bash
pytest -v
```

### Acceptance Test Coverage Matrix:
- **TEST A — SALES WORKFLOW** (`backend/tests/test_a_sales.py`):
  Quotation $\rightarrow$ Sales Order $\rightarrow$ Warehouse Stock Delivery $\rightarrow$ Tax Invoice $\rightarrow$ Partial Collection $\rightarrow$ AR, COGS, Output VAT (14%), WHT (1%), and balanced journal verification.
- **TEST B — PURCHASING & 3-WAY MATCH** (`backend/tests/test_b_purchases.py`):
  PO $\rightarrow$ GRN partial delivery with accepted & rejected inspection quantities $\rightarrow$ Supplier invoice with 3-way match validation $\rightarrow$ Partial supplier payment $\rightarrow$ AP and inventory clearing verification.
- **TEST C — CHEMICAL FORMULATION & PRODUCTION** (`backend/tests/test_c_production.py`):
  Approved formulation recipe $\rightarrow$ Production order $\rightarrow$ Material issue to WIP $\rightarrow$ Finished output batch in quarantine $\rightarrow$ Laboratory QC assay & density testing $\rightarrow$ Batch release & Certificate of Analysis (COA) generation $\rightarrow$ Actual batch costing.
- **TEST D — BIDIRECTIONAL TRACEABILITY** (`backend/tests/test_d_traceability.py`):
  Forward trace (raw material lot to affected customer deliveries) and Reverse trace (finished batch to raw active lots, suppliers, and GRNs) + Recall exposure calculation.
- **TEST E — EXPIRY & QUALITY RELEASE ENFORCEMENT** (`backend/tests/test_e_expiry_quality.py`):
  Guarantees that expired, quarantined, on-hold, or rejected batches are blocked from sales dispatch or production consumption.
- **TEST F — ACCOUNTING INTEGRITY & IDEMPOTENCY** (`backend/tests/test_f_accounting_integrity.py`):
  Balanced journal check, duplicate submission prevention, immutability of posted items, auditable reversal, and closed period enforcement.
- **TEST G — COSTING & VARIANCE ANALYSIS** (`backend/tests/test_g_costing_variance.py`):
  Material Usage Variance (MUV) and Material Price Variance (MPV) calculation against planned recipe values.
- **TEST H — CONCURRENCY & OVERSELLING SAFEGUARDS** (`backend/tests/test_h_concurrency.py`):
  Transactional concurrency locking preventing double-allocation or negative inventory balances.
- **TEST I — AUTHORIZATION & RBAC** (`backend/tests/test_i_authorization.py`):
  Enforces authentication and permissions across all API endpoints.
- **TEST J — BACKUP RESTORATION INTEGRITY** (`backend/tests/test_j_backup_restore.py`):
  Validates relational snapshot export, serialization, and clean database restoration.
- **CHEMICAL DENSITY & UOM CONVERSIONS** (`backend/tests/test_chemical_density_and_conversions.py`):
  Verifies weight-to-volume conversions using product density ($\rho = \text{kg/L}$) and packaging ratios.
- **ETA E-INVOICING ADAPTER** (`backend/tests/test_eta_e_invoicing.py`):
  Validates canonical ETA v1.0 JSON format, SHA-256 hash, and transmission state machine.

---

## 5. Documentation Library

- [Architecture & Technical Specifications](docs/DATABASE_ERD.md)
- [Accounting Posting Rules Matrix](docs/POSTING_RULES.md)
- [Production Deployment & Backup Recovery](docs/DEPLOYMENT_AND_BACKUP.md)
- [Egyptian Tax Authority (ETA) Integration](docs/ETA_E_INVOICING.md)
- [Security & RBAC Matrix](docs/SECURITY_AND_RBAC.md)
- [Third-Party Dependency & License Inventory](docs/THIRD_PARTY_LICENSES.md)
- [Release Notes & Limitations](docs/RELEASE_NOTES.md)
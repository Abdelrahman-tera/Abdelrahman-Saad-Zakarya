# Release Notes & Operational Considerations

## Version 1.0.0 (Production Release)

### Implemented & Verified Capabilities
- **Modular Monolith Backend**: 10 clearly bounded business domain applications (`core`, `accounting`, `inventory`, `sales`, `purchasing`, `manufacturing`, `quality`, `traceability`, `costing`, `tax_egypt`).
- **Complete Double-Entry Accounting Engine**:
  - Immutability of posted journals.
  - Automatic journal posting for GRN clearing, supplier invoices, sales COGS, sales revenue, and collections.
  - Real-time Trial Balance and Income Statement (P&L).
- **Perpetual Inventory & FEFO Picking**:
  - Exact decimal arithmetic for quantities and valuation costs.
  - Chemical batch statuses (`QUARANTINE`, `RELEASED`, `QUALITY_HOLD`, `REJECTED`, `EXPIRED`).
  - Automatic density-based weight/volume conversions ($\rho = \text{kg/L}$).
- **Chemical Formulation & Manufacturing**:
  - Version-controlled Recipes and BOMs with ingredient tolerances and packaging specs.
  - Frozen BOM snapshots on production orders.
  - Real-time material issue to WIP and finished batch quarantine output.
- **QA/QC & Certificate of Analysis (COA)**:
  - Product-specific specifications and parameters (active assay %, density, pH, suspensibility).
  - Enforced quality release workflows.
- **Bidirectional Batch Genealogy & Recall Engine**:
  - Forward trace (raw lot to customers) and reverse trace (product to supplier origins).
  - Market recall exposure and warehouse hold calculations.
- **Industrial Batch Costing & Variance Analysis**:
  - Material Usage Variance (MUV) and Material Price Variance (MPV).
- **Egyptian Tax Authority (ETA) E-Invoicing**:
  - ETA canonical JSON v1.0 schema generation, SHA-256 hash calculation, Activity Code 2012, 14% VAT + 1% WHT, and simulation/live adapter.
- **Enterprise Arabic RTL Interface**:
  - React 19 + TypeScript + Ant Design with complete RTL support, English toggle, role dashboards, and interactive modals.
- **Automated Verification**:
  - Complete automated test suite covering TEST A through TEST J (100% passing).

---

## Known Considerations & Production Recommendations
1. **Hardware HSM Digital Signing Tokens**:
   For live Egyptian Tax Authority production digital signing with physical USB tokens (Egypt Trust / Misr Sign), deploy the signing sidecar agent on a machine with physical USB pass-through or utilize cloud HSM certificates.
2. **PostgreSQL Database Engine**:
   In production, connect to a managed PostgreSQL 16/17/18 cluster with automated WAL archiving for point-in-time recovery (PITR).
3. **Object Storage**:
   Configure AWS S3 or MinIO credentials in `.env` for multi-terabyte attachment storage (safety data sheets, scanned lab results, label artworks).

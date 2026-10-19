# Production Deployment, Backup & Disaster Recovery Guide

This guide covers deployment procedures, environment configuration, database backup automation, and disaster recovery for the Egyptian Agrochemical ERP.

---

## 1. Production Deployment with Docker Compose

### Prerequisites
- Host machine running Linux (Ubuntu 22.04 LTS / 24.04 LTS or Debian 12).
- Docker Engine $\ge 24.0$ and Docker Compose $\ge 2.20$.
- Domain with SSL certificate (Let's Encrypt / Certbot or Managed Ingress).

### Step-by-Step Installation

1. **Clone the Repository**:
   ```bash
   git clone git@github.com:your-company/agrochemical-erp.git /opt/agrochemical-erp
   cd /opt/agrochemical-erp
   ```

2. **Configure Environment Secrets**:
   Copy the provided `.env.example` to `.env` and configure production secrets:
   ```bash
   cp .env.example .env
   chmod 600 .env
   ```
   *Never commit `.env` or production credentials to source control.*

3. **Build & Start Containers**:
   ```bash
   docker compose build
   docker compose up -d
   ```

4. **Initialize Database & Seed Master Data**:
   ```bash
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py seed_demo_data # (Optional demo data)
   docker compose exec backend python manage.py createsuperuser
   ```

5. **Verify Running Services**:
   ```bash
   docker compose ps
   ```
   Expected status:
   - `agro_erp_db`: Up (healthy)
   - `agro_erp_redis`: Up (healthy)
   - `agro_erp_backend`: Up
   - `agro_erp_celery`: Up
   - `agro_erp_frontend`: Up (port 80/443)

---

## 2. Automated PostgreSQL Backup Architecture

Database backups must run automatically, be compressed, encrypted, and synced to off-site object storage (S3-compatible).

### Automated Backup Script (`/opt/agrochemical-erp/scripts/backup.sh`)
```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/var/backups/agrochemical_erp"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql.gz"
CONTAINER_NAME="agro_erp_db"
DB_NAME="agrochemical_erp"
DB_USER="erp_admin"

mkdir -p "${BACKUP_DIR}"

echo "[INFO] Starting database backup at $(date)..."
docker exec -t "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists | gzip > "${BACKUP_FILE}"

echo "[INFO] Backup successfully created: ${BACKUP_FILE} ($(du -sh "${BACKUP_FILE}" | cut -f1))"

# Retention Policy: Delete backups older than 30 days
find "${BACKUP_DIR}" -type f -name "db_backup_*.sql.gz" -mtime +30 -delete
echo "[INFO] Old backups cleaned up according to 30-day retention policy."
```

### Scheduling with Cron
Add to `/etc/cron.d/agrochemical_backup`:
```cron
# Run daily database backup at 02:00 AM Africa/Cairo time
0 2 * * * root /opt/agrochemical-erp/scripts/backup.sh >> /var/log/erp_backup.log 2>&1
```

---

## 3. Disaster Recovery & Database Restoration

To restore a database backup into a clean or disaster-recovery environment:

1. **Verify Backup File Integrity**:
   ```bash
   gzip -t /var/backups/agrochemical_erp/db_backup_20261019_020000.sql.gz
   ```

2. **Restore into PostgreSQL Container**:
   ```bash
   gunzip -c /var/backups/agrochemical_erp/db_backup_20261019_020000.sql.gz | \
     docker exec -i agro_erp_db psql -U erp_admin -d agrochemical_erp
   ```

3. **Run Verification Migrations & Checks**:
   ```bash
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py check --deploy
   ```

4. **Verify Critical Tables & Ledger Balances**:
   Run the automated backup integrity acceptance test:
   ```bash
   docker compose exec backend pytest backend/tests/test_j_backup_restore.py
   ```

# Third-Party Dependencies & Open-Source License Inventory

All dependencies used in the Egyptian Agrochemical ERP have been vetted for commercial compatibility, avoiding viral copyleft licenses (such as AGPL) that could restrict private corporate ownership.

---

## 1. Backend Dependencies (Python)

| Package | Version | Purpose | License | Commercial Permissibility |
| :--- | :--- | :--- | :--- | :--- |
| **Django** | 5.2.18 | Core Web & ORM Framework | BSD 3-Clause | Fully Permitted |
| **djangorestframework** | 3.18.3 | REST API Framework | BSD 3-Clause | Fully Permitted |
| **psycopg** | 3.3.6 | PostgreSQL 16/17/18 Driver | LGPL 3.0 / BSD | Fully Permitted (Binary Wheel) |
| **celery** | 5.6.3 | Asynchronous Task Engine | BSD 3-Clause | Fully Permitted |
| **redis** | 8.1.0 | Redis Client | MIT | Fully Permitted |
| **drf-spectacular** | 0.30.0 | OpenAPI 3.0 Documentation | BSD 3-Clause | Fully Permitted |
| **django-cors-headers** | 4.9.0 | Cross-Origin Request Handling | MIT | Fully Permitted |
| **django-filter** | 26.2 | Declarative Filtering | BSD 3-Clause | Fully Permitted |
| **reportlab** | 5.0.1 | PDF Invoice & COA Generation | BSD License | Fully Permitted |
| **openpyxl** | 3.1.5 | Excel Export / Reporting | MIT | Fully Permitted |
| **python-dotenv** | 1.2.4 | Environment Configuration | BSD 3-Clause | Fully Permitted |
| **cryptography** | 50.0.2 | ETA Hash & Signature Prep | Apache 2.0 / BSD | Fully Permitted |
| **pytest** | 9.1.1 | Automated Test Framework | MIT | Fully Permitted |
| **pytest-django** | 4.14.0 | Django Test Integration | BSD 3-Clause | Fully Permitted |

---

## 2. Frontend Dependencies (Node.js & React)

| Package | Version | Purpose | License | Commercial Permissibility |
| :--- | :--- | :--- | :--- | :--- |
| **react** | 19.0.0 | UI Component Library | MIT | Fully Permitted |
| **react-dom** | 19.0.0 | DOM Renderer | MIT | Fully Permitted |
| **antd** | 5.24.3 | Enterprise UI with Native RTL | MIT | Fully Permitted |
| **@ant-design/icons** | 5.6.1 | UI Icons Library | MIT | Fully Permitted |
| **axios** | 1.8.1 | Typed HTTP API Client | MIT | Fully Permitted |
| **dayjs** | 1.11.13 | Lightweight Date & Time Library | MIT | Fully Permitted |
| **vite** | 6.2.0 | Next-Generation Frontend Tooling | MIT | Fully Permitted |
| **typescript** | 5.7.3 | Static Type Checking | Apache 2.0 | Fully Permitted |

---

## 3. Infrastructure Baseline

| Component | Standard Release | License |
| :--- | :--- | :--- |
| **PostgreSQL** | 16 / 17 / 18 | PostgreSQL License (MIT-style) |
| **Redis** | 7.x | BSD 3-Clause |
| **Nginx** | Alpine / Mainline | 2-Clause BSD |
| **Python** | 3.12 / 3.14 | Python Software Foundation License (PSF) |
| **Node.js** | 22 LTS / 24 | MIT |

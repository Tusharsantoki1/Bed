# GST Billing API

A multi-tenant **GST billing backend** (FastAPI + MySQL) for a mobile billing app.
A multi-tenant **GST billing backend** (FastAPI + PostgreSQL) for a mobile billing app.
Companies register, set up their branding/bank details, add customers (parties),
and generate invoices (with or without GST) as shareable PDFs. A **super admin**
manages companies and their subscriptions.

---

## Who uses it (roles)

| Role | What they do |
|------|--------------|
| **Super admin** | Manages all companies, subscription plans, and grants/cancels subscriptions. |
| **Company admin** | The company login. Sets company profile, logo, bank, signature, stamp; creates invoices; sees the admin-panel dashboard; manages staff. |
| **Company staff** | Optional extra users for a company that can create invoices. |

A company can only create invoices while it has an **active subscription**
(monthly / quarterly / half-yearly / yearly).

---

## Tech

- **FastAPI** (REST API, auto docs at `/docs`)
- **MySQL** via SQLAlchemy 2.0 + PyMySQL
- **PostgreSQL** via SQLAlchemy 2.0 + psycopg2
- **JWT** auth (access + refresh) with bcrypt password hashing
- **fpdf2** for invoice PDF generation
- Images (logo, signature, stamp, payment QR) stored as **base64 in MySQL**
- Images (logo, signature, stamp, payment QR) stored as **base64 in PostgreSQL**

---

## Project structure

```
Bed/
├── requirements.txt
├── .env                      # your config (gitignored) — edit DATABASE_URL
├── .env.example
└── src/
    ├── app.py                # FastAPI app, CORS, router wiring, table creation
    ├── config.py             # settings from .env
    ├── database.py           # engine, session, Base, get_db
    ├── seed.py               # creates super admin + sample plans
    ├── models/               # SQLAlchemy ORM tables
    │   ├── user.py  company.py  party.py  invoice.py  subscription.py  enums.py
    ├── schemas/              # Pydantic request/response models
    ├── services/             # business logic + DB queries
    │   ├── auth_service.py  company_service.py  party_service.py
    │   ├── invoice_service.py  subscription_service.py  plan_service.py
    │   ├── dashboard_service.py  pdf_service.py
    ├── routes/               # API endpoints (thin)
    │   ├── auth.py  company.py  parties.py  invoices.py  dashboard.py  superadmin.py
    └── utils/
        ├── security.py       # password hashing + JWT
        ├── deps.py           # auth / role / subscription guards
        └── numbers.py        # amount-in-words (Indian), money rounding
```

---

## Setup

### 1. Create the database

```sql
-- log in to MySQL, then:
CREATE DATABASE gst_billing CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- log in to psql, then:
CREATE DATABASE gst_billing;
```

### 2. Configure `.env`

A `.env` is already created with a strong random `SECRET_KEY`.
**Edit `DATABASE_URL`** and set your MySQL password:

```
DATABASE_URL=mysql+pymysql://root:YOUR_MYSQL_PASSWORD@127.0.0.1:3306/gst_billing
```

Also change `SUPER_ADMIN_EMAIL` / `SUPER_ADMIN_PASSWORD` to your own.

### 3. Install dependencies

```bash
cd Bed
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Seed the database (creates tables + super admin + sample plans)

```bash
python -m src.seed
```

### 5. Run the server

```bash
uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

- Interactive API docs: **http://localhost:8000/docs**
- Tables are also auto-created on startup.

---

## API overview (prefix `/api`)

### Auth
| Method | Path | Notes |
|--------|------|-------|
| POST | `/auth/register-company` | Sign up a company + admin → returns tokens |
| POST | `/auth/login` | email + password → tokens |
| POST | `/auth/refresh` | refresh token → new access token |
| GET  | `/auth/me` | current user |

### Company (company admin/staff)
| Method | Path | Notes |
|--------|------|-------|
| GET / PATCH | `/company` | view / update profile, bank, invoice prefix |
| PUT | `/company/branding` | upload base64 logo / signature / stamp / payment QR |
| GET | `/company/subscription` | current subscription status |
| GET / POST | `/company/staff` | list / add staff users |
| PATCH | `/company/staff/{id}/active` | enable/disable a staff user |

### Parties (customers)
`GET/POST /parties`, `GET/PATCH/DELETE /parties/{id}`

### Invoices
| Method | Path | Notes |
|--------|------|-------|
| GET | `/invoices` | list (filter by `payment_status`, `party_id`) |
| POST | `/invoices` | **create** (needs active subscription) |
| GET | `/invoices/{id}` | full invoice with items + party |
| PATCH | `/invoices/{id}` | edit (re-computes totals) |
| POST | `/invoices/{id}/payment` | record payment received |
| DELETE | `/invoices/{id}` | delete |
| GET | `/invoices/{id}/pdf` | **download invoice PDF** |

### Dashboards
- `GET /dashboard` — company admin panel (total billed, received, outstanding, counts)
- `GET /admin/dashboard` — super admin overview

### Super admin (`/admin`, super admin only)
- Plans: `GET/POST /admin/plans`, `PATCH/DELETE /admin/plans/{id}`
- Companies: `GET/POST /admin/companies`, `GET /admin/companies/{id}`, `PATCH /admin/companies/{id}/active`
- Subscriptions: `GET/POST /admin/companies/{id}/subscriptions`, `POST /admin/companies/{id}/subscriptions/{sub_id}/cancel`

---

## How GST works

GST is **optional**:

- If the company has **no GSTIN**, invoices are created without tax
  (taxable = net) — exactly like the sample bill.
- If the company **has a GSTIN**, GST is applied per line item using each
  item's `gst_rate` (%). It is split automatically:
  - **Same state** (company state code == party state code) → **CGST + SGST**
  - **Different state** → **IGST**
- You can force behaviour per invoice with `apply_gst`: `true` / `false` /
  omit for auto.

All money totals and the amount-in-words are computed on the **server** — the
mobile app never has to trust client-side math.

---

## Security notes

- Passwords hashed with **bcrypt**; JWT signed with `SECRET_KEY` (keep it secret, ≥32 bytes).
- **Role guards** on every endpoint (super admin vs company vs staff).
- **Tenant isolation**: every company query is scoped by the logged-in user's
  `company_id` — a company can never read/modify another company's data.
- **Subscription gating**: creating invoices returns `402` if the subscription
  is inactive/expired.
- Set a restrictive `CORS_ORIGINS` and serve behind HTTPS in production.
- For production, use **Alembic** migrations instead of auto `create_all`.

---

## Example: create an invoice (matching the sample bill)

```bash
# 1) register a company (or log in) and copy the access_token
curl -X POST localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"owner@eh.com","password":"StrongPass123"}'

# 2) create a non-GST invoice (taxable = net, total 17,900)
curl -X POST localhost:8000/api/invoices \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H 'Content-Type: application/json' \
  -d '{
        "party_id": 1,
        "apply_gst": false,
        "items": [
          {"product_name":"ACCOUTING CHGS","years":"2024-2025","quantity":12,"rate":500},
          {"product_name":"GST RETUNE FEE","years":"2024-2025","quantity":12,"rate":700},
          {"product_name":"INCOME TAX RETUNE FEE","years":"2024-2025","quantity":1,"rate":3500}
        ]
      }'

# 3) download the PDF
curl -L localhost:8000/api/invoices/1/pdf \
  -H "Authorization: Bearer <ACCESS_TOKEN>" -o invoice.pdf
```

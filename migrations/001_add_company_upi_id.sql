-- Adds Company.upi_id: the UPI VPA (e.g. "name@okhdfcbank") printed under the
-- payment QR on the bill. It is distinct from upi_number, which is the G-Pay
-- phone number shown in the bank block.
--
-- WHY THIS FILE EXISTS
-- The app builds its schema with Base.metadata.create_all(), which creates
-- missing TABLES but never alters an existing one. On a database that already
-- has a `companies` table, SQLAlchemy will select companies.upi_id and fail
-- with "Unknown column", breaking every company-scoped route (login, settings,
-- invoices, PDF) — not just the bill.
--
-- Run this ONCE against an existing database before starting the app:
--   mysql -h127.0.0.1 -uroot -p gst_billing < migrations/001_add_company_upi_id.sql
--
-- A brand-new database does not need it: create_all() builds the column.

ALTER TABLE companies
    ADD COLUMN upi_id VARCHAR(100) NULL AFTER upi_number;

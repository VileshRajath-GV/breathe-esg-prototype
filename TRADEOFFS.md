# TRADEOFFS.md: Deliberate Scoping & Exclusions

To deliver a rigorous, auditable prototype, three complex features were deliberately excluded in favour of more deterministic and compliance-safe alternatives.

---

## 1. No PDF OCR Utility Bill Parsing
**Why excluded**: OCR on utility PDF invoices (Tesseract, AWS Textract) is notoriously fragile — layout changes between billing periods break parsers silently. A single misread decimal (e.g. `1` → `7`) causes massive silent reporting errors that fail audit standards.

**Our alternative**: Ingest **Portal CSV Billing Exports**. Billing portals provide clean, structured data. This is the industry-preferred onboarding mechanism for enterprise clients.

---

## 2. No Live Third-Party Emissions Factor API Sync
**Why excluded**: Live carbon factor APIs (Climatiq, UK DEFRA) introduce external dependencies — if the API goes down, ingestion stalls. More critically, factors change annually; an automatic sync can silently retroactively change historical emissions, violating audit baseline locking standards.

**Our alternative**: A versioned **`EmissionFactor` database table** (introduced in the production data model). Each factor record carries `valid_from` / `valid_to` year fields. Factors are pinned to ingestion batches, so calculations are permanently reproducible. This satisfies auditors who require absolute determinism.

---

## 3. No Multi-Tiered RBAC Workflow Engine
**Why excluded**: A full workflow router (Analyst uploads → Manager reviews → Director approves → Auditor locks) involves significant state-machine overhead. For a prototype, building a generic RBAC engine diverts effort from core data quality and normalisation logic.

**Our alternative**: A formal **`ReviewStatus` state machine** (`NEEDS_REVIEW → AUTO_APPROVED → APPROVED → LOCKED`) enforced at the DB model layer, combined with an append-only **`AuditEntry`** log that records every status transition with actor, timestamp, and JSON before/after deltas.

> **Future path**: The `ESGUser.role` field (`ADMIN`, `ANALYST`, `AUDITOR`) and the `ReviewStatus` state machine are designed to be extended into a full role-gated workflow without schema changes.

---

## 4. SQLite → PostgreSQL Upgrade Path (Completed)
**Original prototype**: Used SQLite, which is ephemeral on Render's free tier (wiped on every deploy).

**Production upgrade**: `settings.py` now uses `dj-database-url` to auto-select **PostgreSQL** when `DATABASE_URL` is set (Render injects this from the linked `breathe-esg-db` PostgreSQL service) and falls back to SQLite locally. No manual configuration needed.

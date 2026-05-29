# Breathe ESG — Emissions Ingestion & Normalisation Engine

A production-ready Django REST + React system for enterprise GHG data ingestion, normalisation, auditing, and reporting. Parses messy real-world data streams from SAP, utility portals, and corporate travel platforms, calculates CO₂e, and maintains immutable compliance audit trails.

---

## 📖 Engineering Documentation

| File | Contents |
|---|---|
| [MODEL.md](./MODEL.md) | Full database schema — 9 models, constraints, indexes, state machine |
| [DECISIONS.md](./DECISIONS.md) | Technical & product ambiguity resolutions |
| [SOURCES.md](./SOURCES.md) | Real-world data formats researched & production failure modes |
| [TRADEOFFS.md](./TRADEOFFS.md) | Deliberate exclusions and rationale |

---

## ⚡ Core Features

1. **Multi-Tenancy**: Every record is scoped to a `Tenant`. Cross-tenant data leakage is architecturally impossible.
2. **Role-Based Users**: `ESGUser` with `ADMIN` / `ANALYST` / `AUDITOR` roles.
3. **Messy Stream Normalisation**:
   - **SAP ECC CSV**: German headers (`WERKS`, `MENGE`, etc.), irregular units, German `DD.MM.YYYY` dates, plant code resolution.
   - **Utility Billing CSV**: Daily-average split across calendar months, `MWh → kWh` conversion.
   - **Corporate Travel JSON**: Haversine Great-Circle distance for flights, cabin class multipliers (1.5× business, 2.0× first), hotel room-nights.
4. **Immutable Provenance**: Raw rows stored with SHA-256 checksums — never modified after ingestion.
5. **Versioned Emission Factors**: `EmissionFactor` table with year-range validity — historical calculations remain reproducible.
6. **Review Workflow**: `NEEDS_REVIEW → AUTO_APPROVED → APPROVED → LOCKED` state machine enforced at DB level.
7. **Audit Trail**: Generic append-only `AuditEntry` log with JSON before/after deltas.

---

## 🛠️ Local Setup

### Prerequisites
- Python 3.10+
- Node.js 18+

### Backend (Django)
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Apply all migrations (creates all 9 tables from scratch)
python manage.py migrate

# Seed default tenant + facility profiles
python seed.py

# Start server on port 8000
python manage.py runserver
```

### Frontend (Vite + React)
```bash
cd frontend
npm install
npm run dev          # runs at http://localhost:5173/
```

---

## 🧪 Testing with Sample Data

Sample files are in `/sample_files/`. Run the automated ingestion test:
```bash
cd sample_files
python upload_samples.py
```

Expected output:
```
Processing SAP     from backend_sap_export.csv    → OK: 5 rows
Processing UTILITY from portal_utility_export.csv → OK: 4 rows
Processing TRAVEL  from concur_travel_export.json → OK: 4 rows
```

### Sample files included

| File | Format | Tests |
|---|---|---|
| `backend_sap_export.csv` | SAP ECC flat CSV | German headers, date formats, unit normalisation |
| `portal_utility_export.csv` | Billing portal CSV | Multi-month split, MWh conversion |
| `concur_travel_export.json` | Concur/Navan JSON | Haversine distance, cabin multipliers, hotel nights |

### Backend unit tests
```bash
cd backend
python manage.py test emissions
```

---

## 🚀 Production Deployment (Render)

The `render.yaml` file configures automatic deployment of both services and a managed PostgreSQL database.

### Auto-deploy on push
1. Push to the `main` branch on GitHub.
2. Render detects the push and triggers a new build automatically.
3. Build steps (from `render.yaml`):
   ```
   pip install -r requirements.txt
   python manage.py migrate --noinput   ← all migrations applied automatically
   python seed.py                       ← default tenant + facilities seeded
   ```
4. The server starts via Gunicorn.

### First-time setup on Render
1. Go to [render.com](https://render.com) → **New → Blueprint**.
2. Connect your GitHub repository.
3. Render parses `render.yaml` and provisions:
   - `breathe-esg-db` — free PostgreSQL (data persists across deploys)
   - `breathe-esg-backend` — Django web service (DATABASE_URL injected automatically)
   - `breathe-esg-frontend` — React static site

> **Note:** Render's free PostgreSQL is automatically deleted after **90 days of inactivity**.

### Database
- **Local dev**: SQLite (auto-selected when `DATABASE_URL` is not set)
- **Production (Render)**: PostgreSQL (selected when `DATABASE_URL` env var is present)

Switching is handled automatically in `settings.py` via `dj-database-url` — no manual changes needed.

---

## 🗂️ Project Structure

```
breathe_esg_prototype/
├── backend/
│   ├── config/             # Django settings, URLs, WSGI
│   ├── tenants/            # Tenant + ESGUser models
│   ├── ingestion/          # UploadBatch, RawIngestedRow, parsers
│   ├── emissions/          # FacilityProfile, EmissionFactor, NormalisedEmissionRecord
│   ├── reviews/            # AuditEntry, ReviewComment
│   └── seed.py             # Database seeder
├── frontend/               # Vite + React dashboard
├── sample_files/           # SAP / Utility / Travel test files
├── render.yaml             # Render Blueprint (backend + frontend + PostgreSQL)
├── MODEL.md                # Database schema documentation
├── DECISIONS.md            # Engineering decision log
├── SOURCES.md              # Real-world format research
└── TRADEOFFS.md            # Deliberate exclusions
```

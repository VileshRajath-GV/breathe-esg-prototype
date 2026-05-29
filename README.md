# Breathe ESG Prototype - Emissions Ingestion & Normalization Engine

Welcome to the **Breathe ESG** data ingestion, normalization, and auditing prototype. This application is built as a complete, fully featured Django REST (backend) and React (frontend) system designed to streamline enterprise onboarding by parsing messy raw client streams, executing precise greenhouse gas calculations, and maintaining immutable audit trails.

---

## 📖 Key Engineering Documentation

The following deliverables are included as core architectural files to satisfy regulatory audit review guidelines:

* **[MODEL.md](./MODEL.md) (Data Schemas)**: Exhaustive database blueprints detailing multi-tenant schema isolation, source-of-truth lineages, normalized records, and database-level audit locks.
* **[DECISIONS.md](./DECISIONS.md) (Engineering Decisions)**: Clear justifications for resolving formatting ambiguities across SAP, Utility, and Travel logs, plus future PM alignments.
* **[SOURCES.md](./SOURCES.md) (Real-World Formats & Failure Modes)**: Core research on SAP ECC table structures, billing portal overlapping periods, Concur flight JSONs, and production system failure points.
* **[TRADEOFFS.md](./TRADEOFFS.md) (Scoping & Boundaries)**: Rationale behind deliberate exclusions (such as PDF OCR, live API dependencies, and high-state RBAC workflow managers).

---

## ⚡ Core Features

1. **Active Organization Portal**: Real-time **Multi-Tenancy** selector and new tenant onboarding tool directly in the navigation header.
2. **Messy Stream Normalization**:
   * **SAP ECC Flat CSVs**: Translates German column headers (`WERKS`, `MENGE`, etc.), normalizes irregular units, parses German dates, and resolves plant codes.
   * **Utility Electricity Bills**: Divides usage daily across billing cycles, auto-allocates consumption to matching calendar months, and translates `MWh` $\rightarrow$ `kWh`.
   * **Corporate Travel JSON**: Performs **Great-Circle (Haversine)** distance lookups between airport codes, applies cabin class multipliers (e.g. 1.5x for business), and registers hotel room-nights.
3. **Compliance Audit Trails**: Exposes the **exact raw source JSON row** side-by-side with normalized calculations inside a modal popup. Analysts can add comments to flag rows (`review` / `error`) or **Approve & Lock** them. Once locked, records are database-immunized against any modification or deletion.
4. **Interactive Operations Manual**: Built directly into the hero section via the **"Learn More"** button for instant analyst onboarding.

---

## 🛠️ Installation & Setup (Local Run)

### Prerequisites
* Python 3.10+
* Node.js 18+

### 1. Run Backend (Django)
Navigate to the backend directory, install dependencies, run migrations, seed the database, and start the server:
```bash
cd backend
# Create virtual environment if not present
python -m venv venv
# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
pip install markdown

# Generate and apply migrations
python manage.py makemigrations tenants ingestion emissions reviews
python manage.py migrate

# Seed database (creates default tenant & facility codes)
python seed.py

# Start development server (listens on port 8000)
python manage.py runserver
```

### 2. Run Frontend (Vite + React)
Open a new terminal window:
```bash
cd frontend
# Install dependencies
npm install

# Start local server (runs at http://localhost:5173/)
npm run dev
```

---

## 🚀 Production Deployment Guide

Deploying this prototype to production (which is a mandatory requirement) is simple and streamlined.

### Option A: Render (One-Click Blueprint)
We have included a pre-configured `render.yaml` file in the root directory. This coordinates the build and deploy steps for both the backend (Django Web Service with SQLite) and the frontend (React Static Site) automatically.

1. Push your repository to **GitHub** or **GitLab**.
2. Log in to [Render](https://render.com/).
3. In the Render Dashboard, click **New** -> **Blueprint**.
4. Connect your GitHub repository.
5. Render will automatically parse `render.yaml`, configure the environment variables, set up `VITE_API_URL` dynamically, link them together, and deploy!
6. Once deployed, Render will provide a live URL for your static frontend.

### Option B: Railway Deployment
Railway offers quick, independent web deployments:

1. **Deploy Backend (Django)**:
   - Create a new project on Railway and connect your repository.
   - Set the root directory of the service to `backend/`.
   - Set the Start Command to: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
   - Set Environment Variables:
     - `DEBUG=False`
     - `ALLOWED_HOSTS=*`
   - Railway will provision a public URL for your Django service (e.g., `https://breathe-backend.up.railway.app`).

2. **Deploy Frontend (React)**:
   - Create a second service in the same project, connecting your repository.
   - Set the root directory to `frontend/`.
   - Set Environment Variable:
     - `VITE_API_URL=https://breathe-backend.up.railway.app` (your backend URL)
   - Railway will build and serve your React app statically and link it to your live backend.

---

## 🧪 Testing and Verification

### Automated Unit Tests
To run our high-coverage backend calculation and isolation tests:
```bash
cd backend
.\venv\Scripts\python.exe manage.py test emissions
```

### Manual Testing (Step-by-Step)
We have pre-generated highly realistic sample files for you to test inside your local workspace at `/sample_files/`:
1. **[backend_sap_export.csv](./sample_files/backend_sap_export.csv)**: SAP transaction log with German column names.
2. **[portal_utility_export.csv](./sample_files/portal_utility_export.csv)**: Portal billing CSV with MWh/kWh energy values.
3. **[concur_travel_export.json](./sample_files/concur_travel_export.json)**: JSON booking log with blank flight miles and varying classes.

**Steps to test**:
1. Open the UI at [http://localhost:5173/](http://localhost:5173/).
2. Select **SAP ECC** in the upload zone. Drop `backend_sap_export.csv` into the zone.
3. Watch the Emissions Dashboard charts populate.
4. Scroll down, click **Details** on any row, write an audit rationale, and click **Approve & Lock**.

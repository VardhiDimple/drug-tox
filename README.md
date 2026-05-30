# DRUG TOX PRO

Full-stack web application for **drug-likeness** and **toxicity prediction**. Any valid SMILES string is parsed and analyzed dynamically with **RDKit** on the backend—no hardcoded molecules or static demo pages.

## Features

| Module | Description |
|--------|-------------|
| **ADMET Predictor** | RDKit descriptors (MW, LogP, TPSA, HBD/HBA), Lipinski Rule of Five, rule-based + optional ML toxicity |
| **Molecular Viewer** | 2D structure (RDKit drawing), optional 3D conformer (ETKDG + UFF) with WebGL viewer |
| **ML Classifier** | Upload CSV → Morgan fingerprints → Random Forest → accuracy, ROC curve, AUC |
| **Visualization** | Scatter, correlation heatmap, box plots (Plotly + Matplotlib) |

## Tech stack

- **Backend:** FastAPI, RDKit, scikit-learn, pandas, numpy, matplotlib, plotly
- **Frontend:** Dashboard UI with sidebar navigation (HTML/CSS/JS)

## Quick start

### 1. Create virtual environment (recommended)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** RDKit is easiest via `pip install rdkit`. On some systems, use Conda: `conda install -c conda-forge rdkit`.

### 3. Run the server

```bash
python run.py
```

Open **http://127.0.0.1:8000** in your browser.

## Docker Desktop (local deploy)

Runs **two containers**: `backend` (FastAPI + RDKit) and `frontend` (nginx dashboard that proxies `/api` to the backend).

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running on Windows

### Start the stack

From the project root:

```powershell
cd c:\Users\Kiran\Documents\New-project
docker compose up --build
```

First build may take several minutes (RDKit and scientific packages).

### Open the app

| URL | Service |
|-----|---------|
| **http://localhost:8080** | Dashboard UI (frontend) |
| **http://localhost:8000/api/health** | Backend API only (optional — see below) |

### Useful commands

```powershell
# Run in background
docker compose up --build -d

# View logs
docker compose logs -f

# Stop and remove containers
docker compose down

# Rebuild after code changes
docker compose up --build
```

### Optional: expose backend port for API testing

Add under `backend` in `docker-compose.yml`:

```yaml
    ports:
      - "8000:8000"
```

### Architecture

```
Browser → localhost:8080 → [frontend nginx]
                              ├── /          → index.html + static/
                              └── /api/*     → backend:8000 (FastAPI)
```

## Sample data

Train the ML module with the included dataset:

`data/sample_toxicity.csv` — columns `smiles`, `class` (0 = non-toxic, 1 = toxic)

After training, ADMET toxicity predictions use the trained model automatically.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/admet/predict` | JSON `{ "smiles": "..." }` |
| GET | `/api/molecule/2d?smiles=...` | PNG 2D image |
| GET | `/api/molecule/3d?smiles=...` | 3D coordinates JSON |
| POST | `/api/ml/train` | Multipart CSV + column names |
| POST | `/api/viz/plot` | Multipart CSV + plot options |

## Project structure

```
├── app/
│   ├── main.py              # FastAPI routes
│   ├── schemas.py
│   └── services/
│       ├── admet_service.py
│       ├── descriptors.py
│       ├── molecule_service.py
│       ├── ml_service.py
│       └── viz_service.py
├── static/                  # CSS, JS
├── templates/index.html
├── data/sample_toxicity.csv
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── docker-compose.yml
├── requirements.txt
└── run.py
```

## Example SMILES to try

- Aspirin: `CC(=O)Oc1ccccc1C(=O)O`
- Caffeine: `CN1C=NC2=C1C(=O)N(C(=O)N2C)C`
- Ibuprofen: `CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O`
- Nitrobenzene (toxic alert): `O=[N+]([O-])c1ccccc1`

All outputs are computed at request time from the submitted SMILES.

# Inscriptio

A dysgraphia detection web application powered by a MobileNetV3-Small deep learning model with SHAP explainability. The system allows educators and clinicians to upload handwriting samples, receive AI-generated reports, and track student progress over time.

---

## ⚠️ Python Version Requirement

> **Use Python 3.11.** TensorFlow does **not** support Python 3.12 or higher.

Download Python 3.11 here: https://www.python.org/downloads/release/python-3119/

Verify your version before installing:
```bash
python --version
# Should output: Python 3.11.x
```

---

## Project Structure

```
Inscriptio/
├── inscriptio/               # Frontend (HTML/CSS/JS)
│   ├── html/                 # Page templates
│   ├── css/                  # Stylesheets
│   └── js/                   # Client-side logic
├── model_dev/                # ML pipeline (Python)
│   ├── PHASE_01/             # Preprocessing & augmentation
│   ├── PHASE_02/             # Model training & evaluation
│   ├── PHASE_03/             # Grad-CAM & SHAP explainability
│   └── PHASE_04/             # Full pipeline notebook
└── python/                   # Backend API (FastAPI)
```

---

## Required Downloads

### 1. Python 3.11
TensorFlow only supports Python **3.9–3.11**. Python 3.12+ will fail.

👉 https://www.python.org/downloads/release/python-3119/

During installation on Windows, check **"Add Python to PATH"**.

---

### 2. Git
Used to clone the repository.

👉 https://git-scm.com/downloads

---

### 3. Python Packages
Install all dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

| Package | Purpose |
|---|---|
| `fastapi` | Backend API framework |
| `uvicorn` | ASGI server to run FastAPI |
| `python-multipart` | File upload support |
| `pydantic` / `pydantic-settings` | Data validation & `.env` config |
| `sqlalchemy` | Database ORM (SQLite) |
| `python-jose[cryptography]` | JWT authentication tokens |
| `passlib[bcrypt]` | Password hashing |
| `tensorflow` | Model inference & Grad-CAM (**requires Python 3.11**) |
| `numpy` | Array operations |
| `pandas` | Data handling & manifest CSVs |
| `scikit-learn` | Train/val/test splits |
| `opencv-python` | Image preprocessing (Otsu binarization, resize) |
| `albumentations` | Augmentation pipeline (Phase 1) |
| `scipy` | Elastic distortion augmentation |
| `shap` | SHAP explainability values (Phase 3) |
| `matplotlib` | Visualizations & diagnostic graphics |
| `tqdm` | Progress bars during preprocessing |

---

### 4. Mendeley Handwriting Dataset
The ML pipeline requires the handwriting image dataset. Download it from Mendeley Data and place images under:

```
model_dev/data/raw/LPD/   ← normal handwriting samples
model_dev/data/raw/PD/    ← dysgraphia handwriting samples
```

---

## Setup & Running

### 1. Clone the repository

```bash
git clone https://github.com/kerneldp/Inscriptio.git
cd Inscriptio
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Copy the example env file and edit if needed:

```bash
cd python
cp .env.example .env
```

Default `.env` values work out of the box for local development.

---

## Configuration & Demo Mode

All backend settings are managed through the `.env` file and loaded by `settings.py`, which acts as the central config hub for the entire backend. Every module (`auth.py`, `main.py`, etc.) pulls its values from here — so you never need to hardcode anything directly in the code.

### `.env` Settings Explained

| Setting | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `dev` | Set to `prod` for production |
| `API_TITLE` | `Inscriptio API` | Name shown in API docs |
| `API_VERSION` | `1.0.0` | Version shown in API docs |
| `SECRET_KEY` | `dev-only-change-me` | Signs JWT tokens — **change this in production** |
| `JWT_ALGORITHM` | `HS256` | Token encryption algorithm |
| `TOKEN_EXPIRE_HOURS` | `24` | How long a login session lasts |
| `CORS_ALLOW_ORIGINS` | `http://localhost:5500` | Frontend URLs allowed to call the API |
| `DATABASE_URL` | `sqlite:///./inscriptio.db` | Path to the SQLite database |
| `DEMO_MODE` | `true` | Enables/disables the built-in demo accounts |

### Demo Mode Switch

`DEMO_MODE` works like an on/off switch for the hard-coded demo accounts:

**Demo ON** (`DEMO_MODE=true`) — use this for testing and presentations:
```env
DEMO_MODE=true
```
Enables login with:
| Role | Email | Password |
|---|---|---|
| Educator | `educator@inscriptio.edu` | `educator123` |
| Clinician | `clinician@inscriptio.edu` | `clinician123` |

**Demo OFF** (`DEMO_MODE=false`) — use this for real deployment:
```env
DEMO_MODE=false
```
Demo accounts are disabled. Only users registered via `/api/auth/register` can log in.

> **Important:** Always change `SECRET_KEY` to a long random string before deploying to production.

### 4. Run the backend API

```bash
cd python
python -m uvicorn main:app --reload --port 8000
```

The API will be available at: `http://localhost:8000`
Auto-generated API docs: `http://localhost:8000/docs`

### 5. Run the frontend

Open a **second terminal** at the project root:

```bash
py -m http.server 5500
```

Then open your browser and go to:

```
http://localhost:5500/inscriptio/html/01_authentication_portal.html
```

> **Both servers must be running at the same time** for the app to work.

---

### Test Accounts

| Role | Email | Password |
|---|---|---|
| Educator | `educator@inscriptio.edu` | `educator123` |
| Clinician | `clinician@inscriptio.edu` | `clinician123` |

---

## API Endpoints

### Auth
| Method | URL | Description |
|---|---|---|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, returns token |
| GET | `/api/auth/me` | Get current user info |

### Dashboard
| Method | URL | Description |
|---|---|---|
| GET | `/api/dashboard/summary` | Summary cards data |
| GET | `/api/students?search=` | Student directory |
| GET | `/api/activity/recent` | Latest 4 reports |

### Report & ML Pipeline
| Method | URL | Description |
|---|---|---|
| POST | `/api/report/preprocess/preview` | Upload image, return binarized preview |
| POST | `/api/report/analyze` | Run MobileNetV3 + Grad-CAM + SHAP |
| GET | `/api/report/{report_id}` | Fetch saved report |
| POST | `/api/report/{report_id}/validate` | Clinician verify/disagree |
| PATCH | `/api/report/{report_id}/notes` | Autosave educator notes |
| POST | `/api/report/{report_id}/save` | Commit to student history |

### Progress & Comparison
| Method | URL | Description |
|---|---|---|
| GET | `/api/students/:id/reports` | All reports for a student |
| GET | `/api/students/:id/compare?report1_id=&report2_id=` | Side-by-side comparison |
| GET | `/api/students/:id/trend` | Risk scores over time |

### History
| Method | URL | Description |
|---|---|---|
| GET | `/api/history?date=&student_class=&label=` | Filtered history |
| POST | `/api/history/export` | Bulk export records |
| DELETE | `/api/history/bulk` | Soft delete with reason |

---

## ML Pipeline (model_dev)

Run each phase notebook in order. Make sure Jupyter is installed:

```bash
pip install jupyter
```

### Phase 1 — Preprocessing
**Location:** `model_dev/PHASE_01/`

Standardizes raw images and generates augmented training data.

```bash
cd model_dev/PHASE_01
jupyter notebook preprocessing.ipynb
```

Outputs to:
```
model_dev/data/processed/
model_dev/data/manifests/   (train.csv, val.csv, test.csv)
```

### Phase 2 — Training & Evaluation
**Location:** `model_dev/PHASE_02/`

Trains MobileNetV3-Small in two stages (frozen base → partial unfreeze).

```bash
jupyter notebook training.ipynb
jupyter notebook evaluation.ipynb
jupyter notebook validation.ipynb
```

Outputs to:
```
model_dev/checkpoints/   (FINAL_production_model.keras)
model_dev/logs/
model_dev/reports/
```

### Phase 3 — Explainability
**Location:** `model_dev/PHASE_03/`

Generates Grad-CAM heatmaps and SHAP values for clinical reporting.

```bash
jupyter notebook explainability.ipynb
```

### Phase 4 — Full Pipeline
**Location:** `model_dev/PHASE_04/`

End-to-end run of all phases in a single notebook.

```bash
jupyter notebook inscriptio.ipynb
```

---

## Backend File Structure

```
python/
├── main.py          ← Entry point, run this
├── database.py      ← SQLite connection setup
├── models.py        ← Database tables (User, Student, Report)
├── auth.py          ← Authentication
├── dashboard.py     ← Dashboard endpoints
├── report.py        ← ML pipeline endpoints
├── progress.py      ← Progress & comparison
├── history.py       ← History management
├── settings.py      ← Environment config
├── seed.py          ← Database seeding script
├── requirements.txt ← Python packages
├── .env.example     ← Environment variable template
└── inscriptio.db    ← Auto-created SQLite database
```

---

## Notes

- The frontend calls the backend at `http://localhost:8000` — do not change the port unless you also update `const API` in the JS files.
- Model checkpoints are **not included** in the repository. Run the Phase 2 training notebook to generate `FINAL_production_model.keras` before using the backend API.
- The SQLite database (`inscriptio.db`) is auto-created on first run.

# Inscriptio

A dysgraphia detection web application powered by a MobileNetV3-Small deep learning model with SHAP explainability. The system allows educators and clinicians to upload handwriting samples, receive AI-generated reports, and track student progress over time.

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
└── inscriptio/python/        # Backend API (FastAPI)
```

---

## Requirements

### System

- **Python 3.12**
- **Git**
- A modern browser (Chrome, Edge, Firefox)

### Python Dependencies

Install all at once:

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install tensorflow
pip install numpy pandas scikit-learn
pip install opencv-python
pip install albumentations
pip install scipy
pip install tqdm
pip install shap
pip install matplotlib
pip install fastapi uvicorn
pip install python-multipart
```

| Package | Used In |
|---|---|
| `tensorflow` | Model training, inference, Grad-CAM |
| `numpy` | Array operations across all phases |
| `pandas` | Manifest CSVs, data handling |
| `scikit-learn` | Train/val/test splits |
| `opencv-python` | Image preprocessing (Otsu binarization, resize) |
| `albumentations` | Augmentation pipeline (Phase 1) |
| `scipy` | Elastic distortion augmentation |
| `tqdm` | Progress bars during preprocessing |
| `shap` | SHAP explainability values (Phase 3) |
| `matplotlib` | Visualization, diagnostic graphics |
| `fastapi` | Backend API server |
| `uvicorn` | ASGI server for FastAPI |
| `python-multipart` | File upload handling |

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

### 3. Run the backend API

```bash
cd inscriptio/python
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

### 4. Run the frontend

Open a **second terminal** at the project root:

```bash
py -m http.server 5500
```

Then open your browser and go to:

```
http://localhost:5500/inscriptio/html/01_authentication_portal.html
```

### Test Accounts

| Role | Email | Password |
|---|---|---|
| Educator | `educator@inscriptio.edu` | `educator123` |
| Clinician | `clinician@inscriptio.edu` | `clinician123` |

---

## ML Pipeline (model_dev)

The model development pipeline is split into four phases. Run each notebook in order.

### Phase 1 — Preprocessing
**Location:** `model_dev/PHASE_01/`

Standardizes raw handwriting images and generates augmented training data.

```bash
cd model_dev/PHASE_01
jupyter notebook preprocessing.ipynb
```

Expected data folder structure before running:
```
model_dev/
└── data/
    └── raw/
        ├── LPD/    # Low Potential Dysgraphia samples
        └── PD/     # Potential Dysgraphia samples
```

Outputs to:
```
model_dev/data/processed/
model_dev/data/manifests/   (train.csv, val.csv, test.csv)
```

### Phase 2 — Training & Evaluation
**Location:** `model_dev/PHASE_02/`

Trains a MobileNetV3-Small model in two stages (frozen base → partial unfreeze).

```bash
jupyter notebook training.ipynb
jupyter notebook evaluation.ipynb
jupyter notebook validation.ipynb
```

Outputs to:
```
model_dev/checkpoints/   (production_model.keras, production_model.h5)
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

## Dataset

This project uses the **Mendeley Handwriting Dataset**. Download it and place the images under:

```
model_dev/data/raw/LPD/   ← normal handwriting samples
model_dev/data/raw/PD/    ← dysgraphia handwriting samples
```

---

## Notes

- Both the frontend server (`port 5500`) and backend API (`port 8000`) must be running at the same time for the app to work.
- The frontend calls the backend at `http://localhost:8000` — do not change the port unless you also update `const API` in `inscriptio/js/comparison.js` and other JS files.
- Model checkpoints are not included in the repository. Run the Phase 2 training notebook to generate them before using the backend API.

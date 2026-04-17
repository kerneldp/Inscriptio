"""
AIKONIC — project config (Phase 02 training + evaluation)

This file is intentionally the single source of truth for:
- paths (manifests, outputs)
- model/training hyperparameters for Phase A + Phase B
- metric thresholds used by callbacks and evaluation
"""

from __future__ import annotations

from pathlib import Path

# ── Reproducibility ──────────────────────────────────────────────────────────
RANDOM_SEED = 42

# ── Project paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

MANIFESTS_DIR = DATA_DIR / "manifests"
TRAIN_MANIFEST = str(MANIFESTS_DIR / "train_augmented.csv")  # includes offline 3-tier aug pool
VAL_MANIFEST = str(MANIFESTS_DIR / "val.csv")
TEST_MANIFEST = str(MANIFESTS_DIR / "test.csv")  # must remain unaugmented

CHECKPOINTS_DIR = str(BASE_DIR / "checkpoints")
LOGS_DIR = str(BASE_DIR / "logs")
TRAINING_PLOTS_DIR = str(BASE_DIR / "training_plots")
EVAL_DIR = str(BASE_DIR / "evaluation")
REPORTS_DIR = str(BASE_DIR / "reports")

CHECKPOINT_PHASE_A = str(Path(CHECKPOINTS_DIR) / "phase_a_frozen.h5")
CHECKPOINT_PROD = str(Path(CHECKPOINTS_DIR) / "production_model_final.h5")
TRAINING_METRICS = str(Path(LOGS_DIR) / "training_metrics.csv")

# Native Keras format checkpoints (preferred for TF/Keras >= 2.13).
# H5 is legacy and may fail to reload for nested Functional models.
CHECKPOINT_PHASE_A_KERAS = str(Path(CHECKPOINTS_DIR) / "phase_a_frozen.keras")
CHECKPOINT_PROD_KERAS = str(Path(CHECKPOINTS_DIR) / "production_model_final.keras")

# ── Data/model parameters ────────────────────────────────────────────────────
IMAGE_SIZE = (224, 224)
NUM_CLASSES = 2
CLASS_NAMES = ["LPD", "PD"]  # 0=Low Potential Dysgraphia, 1=Potential Dysgraphia

BATCH_SIZE = 16

DENSE_UNITS = 128
ACTIVATION = "hard_swish"
DROPOUT_RATE = 0.4

# ── Phase A: frozen base ─────────────────────────────────────────────────────
PHASE_A_LR = 1e-4
PHASE_A_EPOCHS = 30
PHASE_A_ES_PATIENCE = 10

# ── Phase B: full unfreeze ───────────────────────────────────────────────────
PHASE_B_LR = 1e-6
PHASE_B_EPOCHS = 50
PHASE_B_ES_PATIENCE = 10

# ── Clinical target (primary metric) ─────────────────────────────────────────
SENSITIVITY_THRESHOLD = 0.85

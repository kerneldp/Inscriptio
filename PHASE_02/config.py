"""
AIKONIC — config.py
"""

from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# PROJECT DIRECTORIES (Centralized Mother Folder Setup)
# ─────────────────────────────────────────────────────────────────────────────
# This finds the folder the script is currently in (e.g., PHASE_1 or PHASE_2)
CURRENT_PHASE_DIR = Path(__file__).resolve().parent

# This reaches UP one level to the main Aikonic folder
MOTHER_DIR = CURRENT_PHASE_DIR.parent

# Shared Data Folders
DATA_DIR = MOTHER_DIR / "data"
RAW_DIR = DATA_DIR / "raw"  # original Mendeley images
PROCESSED_DIR = DATA_DIR / "processed"  # standardized PNGs
MANIFESTS_DIR = DATA_DIR / "manifests"  # CSV files

TRAIN_MANIFEST = MANIFESTS_DIR / "train.csv"
VAL_MANIFEST = MANIFESTS_DIR / "val.csv"
TEST_MANIFEST = MANIFESTS_DIR / "test.csv"

# Shared Output Paths (Accessible by Phase 3 later)
CHECKPOINTS_DIR = MOTHER_DIR / "checkpoints"
LOGS_DIR = MOTHER_DIR / "logs"
REPORTS_DIR = MOTHER_DIR / "reports"
EVAL_DIR = MOTHER_DIR / "evaluation"
TRAINING_PLOTS_DIR = MOTHER_DIR / "training_plots"

# Model checkpoint files
CHECKPOINT_PHASE_A_KERAS = str(CHECKPOINTS_DIR / "phase_a_best.keras")
CHECKPOINT_PROD_KERAS = str(CHECKPOINTS_DIR / "production_model.keras")
CHECKPOINT_PROD = str(CHECKPOINTS_DIR / "production_model.h5")

# Log / report files
TRAINING_METRICS = str(LOGS_DIR / "training_metrics.csv")
ARCH_SUMMARY = str(REPORTS_DIR / "architecture_summary.txt")

# ─────────────────────────────────────────────────────────────────────────────
# DATASET
# ─────────────────────────────────────────────────────────────────────────────
CLASSES = ["LPD", "PD"]  # 0 = LPD (normal), 1 = PD (dysgraphia)
CLASS_NAMES = CLASSES
NUM_CLASSES = 2
RANDOM_SEED = 42

# ─────────────────────────────────────────────────────────────────────────────
# PREPROCESSING
# ─────────────────────────────────────────────────────────────────────────────
IMAGE_SIZE = (224, 224)  # MobileNetV3-Small standard input
AUGMENT_TARGET = 5000  # augmented images per class in training split

SPLIT_VAL_SIZE = 0.15
SPLIT_TEST_SIZE = 0.15

# Elastic distortion
ELASTIC_ALPHA = 1.5
ELASTIC_SIGMA = 0.09  # normalized to image width

# Augmentation tier weights
TIER_WEIGHTS = {
    "tier1": 0.55,
    "tier2": 0.15,
    "tier3": 0.30,
}

# ─────────────────────────────────────────────────────────────────────────────
# MODEL ARCHITECTURE
# ─────────────────────────────────────────────────────────────────────────────
DENSE_UNITS = 128
ACTIVATION = "hard_swish"
DROPOUT_RATE = 0.5
GRAD_CAM_LAYER = "Conv_2"  # last conv layer name in MobileNetV3-Small

# ─────────────────────────────────────────────────────────────────────────────
# TRAINING HYPERPARAMETERS
# ─────────────────────────────────────────────────────────────────────────────
BATCH_SIZE = 16

# Phase A — frozen MobileNetV3-Small base, train head only
PHASE_A_LR = 1e-4
PHASE_A_EPOCHS = 30
PHASE_A_ES_PATIENCE = 10

# Phase B — partial unfreeze (top 20% of base layers)
PHASE_B_LR = 5e-7
PHASE_B_EPOCHS = 50
PHASE_B_ES_PATIENCE = 15
PHASE_B_UNFREEZE_FRACTION = 0.20

# ─────────────────────────────────────────────────────────────────────────────
# EVALUATION THRESHOLDS
# ─────────────────────────────────────────────────────────────────────────────
TARGET_ACCURACY = 0.88
SENSITIVITY_THRESHOLD = 0.85

# ─────────────────────────────────────────────────────────────────────────────
# CROSS-VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
CV_FOLDS = 5
CV_EPOCHS = 30
CV_ES_PATIENCE = 7

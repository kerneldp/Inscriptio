"""
config.py — Central configuration for Phase 01 preprocessing pipeline.
All augmentation hyperparameters and random seeds live here for full reproducibility.
"""

# ── Reproducibility ────────────────────────────────────────────────────────────
SEED = 42

# ── Dataset paths ──────────────────────────────────────────────────────────────
RAW_MENDELEY_DIR  = "data/raw/mendeley/DATASET DYSGRAPHIA HANDWRITING"
PROCESSED_DIR     = "data/processed"
AUGMENTED_DIR     = "data/augmented"
MANIFESTS_DIR     = "data/manifests"
REPORTS_DIR       = "reports"
SPOTCHECK_DIR     = "reports/spotcheck"

# ── Split ratios ───────────────────────────────────────────────────────────────
TRAIN_RATIO = 0.50
VAL_RATIO   = 0.25
TEST_RATIO  = 0.25

# ── Preprocessing ──────────────────────────────────────────────────────────────
TARGET_SIZE = (224, 224)   # (width, height) for cv2.resize

# ── Tier 1 — Geometric transforms (Keras ImageDataGenerator) ──────────────────
TIER1_PARAMS = {
    "rotation_range":     15,
    "zoom_range":         0.15,
    "width_shift_range":  0.12,
    "height_shift_range": 0.12,
    "shear_range":        0.08,
    "horizontal_flip":    False,   # letter orientation must be preserved
    "fill_mode":          "nearest",
}

# ── Tier 2 — Elastic distortion (simulates motor-control micro-tremors) ────────
ELASTIC_PARAMS = {
    "grid_spacing":   60,      # control-point grid at 40-80px intervals
    "alpha":          8.0,     # displacement magnitude (lock after calibration)
    "sigma":          3.5,     # smoothing sigma for displacement vectors
    "interpolation":  "bicubic",   # cv2.INTER_CUBIC
}

# ── Tier 3 — Photometric perturbations (classroom camera conditions) ───────────
TIER3_PARAMS = {
    "gaussian_noise_mean":    0.0,
    "gaussian_noise_sigma":   0.01,    # σ²=0.01
    "gaussian_blur_kernel":   (3, 3),
    "brightness_jitter":      0.15,    # ±15%
    "salt_pepper_prob":       0.005,
}

# ── Augmentation pool size target ─────────────────────────────────────────────
# Final augmented pool must be ≥10× the original training set size
MIN_AUG_MULTIPLIER = 10

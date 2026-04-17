"""
AIKONIC — callbacks.py
Training callbacks: ModelCheckpoint, EarlyStopping, SensitivityMonitor, CSVLogger.
"""

import tensorflow as tf
import numpy as np
import csv, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


class SensitivityMonitor(tf.keras.callbacks.Callback):
    """
    Monitors Recall (Sensitivity) on the validation set each epoch.
    If Sensitivity < SENSITIVITY_THRESHOLD, logs a warning and can
    dynamically raise Dropout to 0.5 or apply label smoothing.

    Parameters
    ----------
    threshold : float  — alert threshold (default 0.85)
    auto_adjust : bool — if True, raise Dropout to 0.5 when breached
    """

    def __init__(self, threshold: float = config.SENSITIVITY_THRESHOLD,
                 auto_adjust: bool = True):
        super().__init__()
        self.threshold = threshold
        self.auto_adjust = auto_adjust
        self._adjusted = False

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        # Keras metric name is 'val_recall'
        sensitivity = logs.get("val_recall", None)
        if sensitivity is None:
            return

        status = "✓" if sensitivity >= self.threshold else "✗"
        print(f"  [SensitivityMonitor] Epoch {epoch+1:03d} | "
              f"Sensitivity={sensitivity:.4f} {status} (threshold={self.threshold})")

        if sensitivity < self.threshold:
            print(f"  ⚠  Sensitivity below {self.threshold:.0%} — consider raising "
                  f"Dropout to 0.5 or applying label smoothing.")

            if self.auto_adjust and not self._adjusted:
                for layer in self.model.layers:
                    if isinstance(layer, tf.keras.layers.Dropout):
                        layer.rate = 0.5
                        self._adjusted = True
                        print(f"  [SensitivityMonitor] Dropout automatically raised to 0.5")
                        break


def get_phase_a_callbacks(checkpoint_path: str = config.CHECKPOINT_PHASE_A_KERAS,
                          metrics_csv: str = config.TRAINING_METRICS) -> list:
    """Return callbacks for Phase A (frozen base) training."""
    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
    os.makedirs(os.path.dirname(metrics_csv), exist_ok=True)

    return [
        tf.keras.callbacks.ModelCheckpoint(
            filepath=checkpoint_path,
            monitor="val_loss",
            save_best_only=True,
            save_weights_only=False,
            verbose=1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=config.PHASE_A_ES_PATIENCE,
            restore_best_weights=True,
            verbose=1,
        ),
        tf.keras.callbacks.CSVLogger(
            metrics_csv,
            append=False,   # Phase A starts fresh
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=5,
            min_lr=1e-7,
            verbose=1,
        ),
    ]


def get_phase_b_callbacks(checkpoint_path: str = config.CHECKPOINT_PROD_KERAS,
                          metrics_csv: str = config.TRAINING_METRICS) -> list:
    """Return callbacks for Phase B (full unfreeze) training."""
    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)

    return [
        tf.keras.callbacks.ModelCheckpoint(
            filepath=checkpoint_path,
            monitor="val_loss",
            save_best_only=True,
            save_weights_only=False,
            verbose=1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=config.PHASE_B_ES_PATIENCE,
            restore_best_weights=True,
            verbose=1,
        ),
        SensitivityMonitor(
            threshold=config.SENSITIVITY_THRESHOLD,
            auto_adjust=True,
        ),
        tf.keras.callbacks.CSVLogger(
            metrics_csv,
            append=True,    # Phase B appends to same CSV
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.3,
            patience=5,
            min_lr=1e-8,
            verbose=1,
        ),
    ]

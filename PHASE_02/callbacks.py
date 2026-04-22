"""
AIKONIC — callbacks.py
======================
Training callbacks for Phase A and Phase B.
Imported by the training notebook only.
"""

import os, sys
import tensorflow as tf

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import config


class SensitivityMonitor(tf.keras.callbacks.Callback):
    """
    Monitors val_recall (sensitivity) each epoch.

    If sensitivity falls below SENSITIVITY_THRESHOLD, logs a warning.
    With auto_adjust=True, raises Dropout to 0.5 once as a soft corrective.

    Parameters
    ----------
    threshold    : float  alert threshold (default config.SENSITIVITY_THRESHOLD)
    auto_adjust  : bool   if True, raise Dropout rate once when breached
    """

    def __init__(
        self,
        threshold: float = config.SENSITIVITY_THRESHOLD,
        auto_adjust: bool = True,
    ):
        super().__init__()
        self.threshold   = threshold
        self.auto_adjust = auto_adjust
        self._adjusted   = False

    def on_epoch_end(self, epoch, logs=None):
        logs        = logs or {}
        sensitivity = logs.get("val_recall", None)
        if sensitivity is None:
            return

        status = "✓" if sensitivity >= self.threshold else "✗"
        print(
            f"  [SensitivityMonitor] Epoch {epoch+1:03d} | "
            f"Sensitivity={sensitivity:.4f} {status} "
            f"(threshold={self.threshold})"
        )

        if sensitivity < self.threshold:
            print(
                f"  ⚠  Sensitivity below {self.threshold:.0%} — "
                f"consider raising Dropout or applying label smoothing."
            )
            if self.auto_adjust and not self._adjusted:
                for layer in self.model.layers:
                    if isinstance(layer, tf.keras.layers.Dropout):
                        layer.rate   = 0.5
                        self._adjusted = True
                        print(
                            f"  [SensitivityMonitor] Dropout automatically "
                            f"raised to 0.5"
                        )
                        break


def get_phase_a_callbacks(
    checkpoint_path: str = config.CHECKPOINT_PHASE_A_KERAS,
    metrics_csv: str     = config.TRAINING_METRICS,
) -> list:
    """
    Callbacks for Phase A (frozen base, head training only).

    Includes
    --------
    - ModelCheckpoint  : saves best val_loss checkpoint
    - EarlyStopping    : patience=PHASE_A_ES_PATIENCE, restores best weights
    - CSVLogger        : writes epoch metrics to training_metrics.csv (fresh)
    - ReduceLROnPlateau: halves LR on plateau, floor at 1e-7
    """
    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
    os.makedirs(os.path.dirname(metrics_csv),     exist_ok=True)

    return [
        tf.keras.callbacks.ModelCheckpoint(
            filepath        = checkpoint_path,
            monitor         = "val_loss",
            save_best_only  = True,
            save_weights_only = False,
            verbose         = 1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor             = "val_loss",
            patience            = config.PHASE_A_ES_PATIENCE,
            restore_best_weights= True,
            verbose             = 1,
        ),
        tf.keras.callbacks.CSVLogger(
            metrics_csv,
            append = False,     # Phase A starts a fresh log
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor  = "val_loss",
            factor   = 0.5,
            patience = 5,
            min_lr   = 1e-7,
            verbose  = 1,
        ),
    ]


def get_phase_b_callbacks(
    checkpoint_path: str = config.CHECKPOINT_PROD_KERAS,
    metrics_csv: str     = config.TRAINING_METRICS,
) -> list:
    """
    Callbacks for Phase B (partial unfreeze, domain adaptation).

    Differences from Phase A
    ------------------------
    - More aggressive ReduceLROnPlateau (factor=0.3, floor=1e-8)
    - Longer EarlyStopping patience (PHASE_B_ES_PATIENCE)
    - SensitivityMonitor added
    - CSVLogger appends to same file (continuous training log)
    """
    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)

    return [
        tf.keras.callbacks.ModelCheckpoint(
            filepath          = checkpoint_path,
            monitor           = "val_loss",
            save_best_only    = True,
            save_weights_only = False,
            verbose           = 1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor              = "val_loss",
            patience             = config.PHASE_B_ES_PATIENCE,
            restore_best_weights = True,
            verbose              = 1,
        ),
        SensitivityMonitor(
            threshold   = config.SENSITIVITY_THRESHOLD,
            auto_adjust = True,
        ),
        tf.keras.callbacks.CSVLogger(
            metrics_csv,
            append = True,      # Phase B appends — continuous log across both phases
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor  = "val_loss",
            factor   = 0.3,
            patience = 5,
            min_lr   = 1e-8,
            verbose  = 1,
        ),
    ]

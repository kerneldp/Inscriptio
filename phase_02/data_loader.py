"""
AIKONIC — data_loader.py
Loads train/val/test splits from manifest CSVs into tf.data.Dataset pipelines.
Augmentation is applied to TRAINING split ONLY.
"""

import tensorflow as tf
import pandas as pd
import numpy as np
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))
import config


# ─────────────────────────────────────────────────────────────────────────────
# Low-level image reader
# ─────────────────────────────────────────────────────────────────────────────

def _maybe_rewrite_manifest_path(path: str) -> str:
    """
    Manifest CSVs may contain absolute paths from another machine.
    If the path doesn't exist, attempt to rewrite it to the current repo path.

    Strategy:
    - If path exists: return as-is
    - Else: locate the portion after ".../aikonic/" or "...\\aikonic\\"
      and join it with this workspace's BASE_DIR.
    """
    if not path:
        return path
    if os.path.exists(path):
        return path

    lower = path.lower()
    anchor = "\\aikonic\\"
    idx = lower.find(anchor)
    if idx != -1:
        rel = path[idx + len(anchor) :].lstrip("\\/")  # keep relative subpath
        candidate = os.path.join(str(config.BASE_DIR), rel)
        if os.path.exists(candidate):
            return candidate

    # Fallback: try to detect ".../data/..." segment and re-root it.
    for seg in ["\\data\\", "/data/"]:
        idx2 = lower.find(seg)
        if idx2 != -1:
            rel2 = path[idx2 + 1 :].lstrip("\\/")  # "data/..."
            candidate2 = os.path.join(str(config.BASE_DIR), rel2)
            if os.path.exists(candidate2):
                return candidate2

    return path


def _load_image(path: str) -> tf.Tensor:
    """Read image from disk → float32 tensor (224, 224, 1), range [0, 1]."""
    path = _maybe_rewrite_manifest_path(path)
    raw = tf.io.read_file(path)
    img = tf.image.decode_jpeg(raw, channels=1)
    img = tf.cast(img, tf.float32) / 255.0
    img = tf.image.resize(img, config.IMAGE_SIZE)
    return img


def _load_sample(path, label):
    return _load_image(path), label


# ─────────────────────────────────────────────────────────────────────────────
# DataLoader class
# ─────────────────────────────────────────────────────────────────────────────

class DataLoader:
    """
    Builds tf.data pipelines from manifest CSVs.

    Manifest CSV columns: image_path, label (int 0/1), augmented (bool)

    Usage
    -----
    loader = DataLoader()
    train_ds = loader.get_train_dataset()
    val_ds   = loader.get_val_dataset()
    test_ds  = loader.get_test_dataset()
    """

    def __init__(
        self,
        train_csv: str = config.TRAIN_MANIFEST,
        val_csv:   str = config.VAL_MANIFEST,
        test_csv:  str = config.TEST_MANIFEST,
        batch_size: int = config.BATCH_SIZE,
        seed: int = config.RANDOM_SEED,
    ):
        self.train_csv  = train_csv
        self.val_csv    = val_csv
        self.test_csv   = test_csv
        self.batch_size = batch_size
        self.seed       = seed

        self._train_df = self._read_manifest(train_csv)
        self._val_df   = self._read_manifest(val_csv)
        self._test_df  = self._read_manifest(test_csv)

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _read_manifest(csv_path: str) -> pd.DataFrame:
        if not os.path.exists(csv_path):
            raise FileNotFoundError(
                f"Manifest not found: {csv_path}\n"
                "Run Phase 1 (partitioning + augmentation) first."
            )
        df = pd.read_csv(csv_path)
        required = {"image_path", "label"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Manifest {csv_path} missing columns: {missing}")
        # Normalize any foreign absolute paths to this repo when possible.
        df["image_path"] = df["image_path"].astype(str).map(_maybe_rewrite_manifest_path)
        return df

    def _df_to_dataset(
        self,
        df: pd.DataFrame,
        shuffle: bool = False,
        augment: bool = False,
    ) -> tf.data.Dataset:
        paths  = df["image_path"].tolist()
        labels = tf.keras.utils.to_categorical(
            df["label"].tolist(), num_classes=config.NUM_CLASSES
        )
        labels = labels.astype("float32")

        ds = tf.data.Dataset.from_tensor_slices((paths, labels))
        ds = ds.map(_load_sample, num_parallel_calls=tf.data.AUTOTUNE)

        if shuffle:
            ds = ds.shuffle(buffer_size=len(df), seed=self.seed)

        ds = ds.batch(self.batch_size)
        ds = ds.prefetch(tf.data.AUTOTUNE)
        return ds

    # ── public API ────────────────────────────────────────────────────────────

    def get_train_dataset(self) -> tf.data.Dataset:
        """Returns shuffled, batched training dataset."""
        return self._df_to_dataset(self._train_df, shuffle=True, augment=True)

    def get_val_dataset(self) -> tf.data.Dataset:
        """Returns batched validation dataset (no augmentation)."""
        return self._df_to_dataset(self._val_df, shuffle=False, augment=False)

    def get_test_dataset(self) -> tf.data.Dataset:
        """Returns batched test dataset (original, unaugmented Mendeley images only)."""
        # Guard: test set must never contain augmented images
        if "augmented" in self._test_df.columns:
            aug_count = self._test_df["augmented"].sum()
            assert aug_count == 0, (
                f"INTEGRITY ERROR: {aug_count} augmented images found in test split. "
                "Test set must contain original unaugmented Mendeley samples ONLY."
            )
        return self._df_to_dataset(self._test_df, shuffle=False, augment=False)

    def get_arrays(self, split: str) -> tuple[np.ndarray, np.ndarray]:
        """
        Load an entire split into numpy arrays (X, y) for evaluation/CV.
        - X shape: (N, 224, 224, 1) float32 in [0, 1]
        - y shape: (N,) int labels {0,1}
        """
        split = split.lower().strip()
        if split == "train":
            df = self._train_df
        elif split == "val":
            df = self._val_df
        elif split == "test":
            df = self._test_df
        else:
            raise ValueError("split must be one of: 'train', 'val', 'test'")

        paths = df["image_path"].astype(str).tolist()
        y = df["label"].astype(int).to_numpy()

        # Load images eagerly using the same tf ops (keeps preprocessing identical)
        xs = []
        for p in paths:
            img = _load_image(p)
            xs.append(img.numpy())
        X = np.stack(xs, axis=0).astype("float32")
        return X, y

    def get_class_weights(self) -> dict:
        """
        Compute class weights from training manifest to address PD/LPD imbalance.
        Returns dict {0: w_lpd, 1: w_pd} for use in model.fit(class_weight=...).
        """
        from sklearn.utils.class_weight import compute_class_weight
        labels = self._train_df["label"].values
        classes = np.unique(labels)
        weights = compute_class_weight("balanced", classes=classes, y=labels)
        cw = {int(c): float(w) for c, w in zip(classes, weights)}
        print(f"[DataLoader] Class weights: {cw}")
        return cw

    def get_sample_counts(self) -> dict:
        """Return sample counts per split."""
        return {
            "train": len(self._train_df),
            "val":   len(self._val_df),
            "test":  len(self._test_df),
        }

    def validate_no_leakage(self):
        """Assert zero filename collisions across all three splits."""
        def _basenames(df):
            return set(df["image_path"].apply(os.path.basename))

        train_b = _basenames(self._train_df)
        val_b   = _basenames(self._val_df)
        test_b  = _basenames(self._test_df)

        tv = train_b & val_b
        tt = train_b & test_b
        vt = val_b   & test_b

        collisions = tv | tt | vt
        assert len(collisions) == 0, (
            f"DATA LEAKAGE DETECTED — {len(collisions)} filename collisions across splits: "
            f"{list(collisions)[:10]}"
        )
        print("[DataLoader] ✓ Zero data leakage verified across all splits.")


# ─────────────────────────────────────────────────────────────────────────────
# Quick smoke test (run directly: python data_loader.py)
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    loader = DataLoader()
    counts = loader.get_sample_counts()
    print(f"Split counts: {counts}")
    loader.validate_no_leakage()
    cw = loader.get_class_weights()

    for split_name, ds in [
        ("train", loader.get_train_dataset()),
        ("val",   loader.get_val_dataset()),
        ("test",  loader.get_test_dataset()),
    ]:
        for batch_imgs, batch_labels in ds.take(1):
            shape = batch_imgs.shape
            dtype = batch_imgs.dtype
            pmin  = float(tf.reduce_min(batch_imgs))
            pmax  = float(tf.reduce_max(batch_imgs))
            print(f"[{split_name:5s}] batch shape={shape} | dtype={dtype} | "
                  f"pixel range=[{pmin:.3f}, {pmax:.3f}]")
            assert shape[1:] == (224, 224, 1), f"Unexpected shape: {shape}"
            assert dtype == tf.float32
            assert pmin >= 0.0 and pmax <= 1.0
    print("✓ All DataLoader assertions passed.")

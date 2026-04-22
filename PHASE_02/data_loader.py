"""
AIKONIC — data_loader.py
========================
Loads train/val/test splits from manifest CSVs into tf.data pipelines.

Design decisions
----------------
- Augmentation is OFFLINE: aikonic_preprocessing.py generates augmented
  PNGs before training. The manifests already include augmented image paths.
  This loader does NOT apply online augmentation.
- Standardization (Otsu binarization, inversion, resize) is also OFFLINE.
  _load_image() assumes inputs are already standardized PNGs.
- Test split integrity is enforced: augmented images are blocked from test.
- Path rewriting handles manifests generated on a different machine.
"""

import os, sys
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.utils.class_weight import compute_class_weight

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import config


# ─────────────────────────────────────────────────────────────────────────────
# Path rewriting utility
# ─────────────────────────────────────────────────────────────────────────────


def _rewrite_path(path: str) -> str:
    """
    Manifest CSVs may contain absolute paths from a different machine.
    Attempts to reroot the path to the current BASE_DIR if the file
    doesn't exist at the original location.
    """
    if not path:
        return path
    if os.path.exists(path):
        return path

    lower = path.lower()
    for anchor in ["\\aikonic\\", "/aikonic/"]:
        idx = lower.find(anchor)
        if idx != -1:
            rel = path[idx + len(anchor) :].lstrip("\\/")
            candidate = os.path.join(str(config.BASE_DIR), rel)
            if os.path.exists(candidate):
                return candidate

    for seg in ["\\data\\", "/data/"]:
        idx = lower.find(seg)
        if idx != -1:
            rel = path[idx + 1 :].lstrip("\\/")
            candidate = os.path.join(str(config.BASE_DIR), rel)
            if os.path.exists(candidate):
                return candidate

    return path  # return original; will fail loudly at read time


# ─────────────────────────────────────────────────────────────────────────────
# Low-level image reader
# ─────────────────────────────────────────────────────────────────────────────


def _load_image(path: tf.Tensor) -> tf.Tensor:
    """
    Read a standardized PNG/JPEG from disk → float32 tensor (224, 224, 1).

    Assumptions
    -----------
    - Input images have already been standardized by aikonic_preprocessing.py:
        Otsu binarization → inversion normalization → bilinear resize → [0,1]
    - All formats (PNG, JPEG, BMP) are handled via decode_image.

    Returns
    -------
    tf.Tensor of shape (224, 224, 1), dtype float32, pixel range [0.0, 1.0]
    """
    raw = tf.io.read_file(path)
    img = tf.image.decode_image(
        raw,
        channels=1,
        expand_animations=False,  # reject GIFs
    )
    img = tf.cast(img, tf.float32) / 255.0
    img = tf.image.resize(
        img,
        config.IMAGE_SIZE,
        method=tf.image.ResizeMethod.BILINEAR,
    )
    img.set_shape([config.IMAGE_SIZE[0], config.IMAGE_SIZE[1], 1])
    return img


def _load_sample(path, label):
    return _load_image(path), label


# ─────────────────────────────────────────────────────────────────────────────
# DataLoader
# ─────────────────────────────────────────────────────────────────────────────


class DataLoader:
    """
    Builds tf.data pipelines from manifest CSVs.

    Manifest CSV columns
    --------------------
    image_path : str   absolute path to standardized PNG
    label      : int   0 = LPD (normal), 1 = PD (dysgraphia)
    augmented  : bool  True if this row is an augmented sample

    Usage
    -----
    loader   = DataLoader()
    train_ds = loader.get_train_dataset()
    val_ds   = loader.get_val_dataset()
    test_ds  = loader.get_test_dataset()    # original images only
    X, y     = loader.get_arrays('test')    # numpy arrays for sklearn metrics
    """

    def __init__(
        self,
        train_csv: str = str(config.TRAIN_MANIFEST),
        val_csv: str = str(config.VAL_MANIFEST),
        test_csv: str = str(config.TEST_MANIFEST),
        batch_size: int = config.BATCH_SIZE,
        seed: int = config.RANDOM_SEED,
    ):
        self.batch_size = batch_size
        self.seed = seed

        self._train_df = self._read_manifest(train_csv)
        self._val_df = self._read_manifest(val_csv)
        self._test_df = self._read_manifest(test_csv)

        # Enforce test set integrity at construction time
        self._assert_test_integrity()

    # ── private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _read_manifest(csv_path: str) -> pd.DataFrame:
        if not os.path.exists(csv_path):
            raise FileNotFoundError(
                f"Manifest not found: {csv_path}\n"
                "Run aikonic_preprocessing.py first to generate manifests."
            )
        df = pd.read_csv(csv_path)

        required = {"image_path", "label"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"Manifest {csv_path} is missing required columns: {missing}"
            )

        # Normalize paths for cross-machine compatibility
        df["image_path"] = df["image_path"].astype(str).map(_rewrite_path)
        return df

    def _assert_test_integrity(self):
        """Block augmented images from ever entering the test split."""
        if "augmented" not in self._test_df.columns:
            return
        aug_count = int(self._test_df["augmented"].sum())
        assert aug_count == 0, (
            f"INTEGRITY ERROR: {aug_count} augmented image(s) found in the "
            "test manifest. Test set must contain original unaugmented "
            "Mendeley samples ONLY. Re-run aikonic_preprocessing.py."
        )

    def _df_to_dataset(
        self,
        df: pd.DataFrame,
        shuffle: bool = False,
    ) -> tf.data.Dataset:
        paths = df["image_path"].tolist()
        labels = tf.keras.utils.to_categorical(
            df["label"].tolist(), num_classes=config.NUM_CLASSES
        ).astype("float32")

        ds = tf.data.Dataset.from_tensor_slices((paths, labels))
        ds = ds.map(_load_sample, num_parallel_calls=tf.data.AUTOTUNE)

        # ADD THIS LINE HERE: Loads the dataset into Colab's RAM after the first read
        ds = ds.cache()

        if shuffle:
            ds = ds.shuffle(buffer_size=len(df), seed=self.seed)

        ds = ds.batch(self.batch_size)
        ds = ds.prefetch(tf.data.AUTOTUNE)
        return ds

    # ── public API ────────────────────────────────────────────────────────────

    def get_train_dataset(self) -> tf.data.Dataset:
        """Shuffled, batched training dataset (includes augmented images)."""
        return self._df_to_dataset(self._train_df, shuffle=True)

    def get_val_dataset(self) -> tf.data.Dataset:
        """Batched validation dataset. No augmentation, no shuffle."""
        return self._df_to_dataset(self._val_df, shuffle=False)

    def get_test_dataset(self) -> tf.data.Dataset:
        """Batched test dataset. Original unaugmented Mendeley images only."""
        return self._df_to_dataset(self._test_df, shuffle=False)

    def get_arrays(self, split: str, return_paths: bool = False):
        """
        Load an entire split into numpy arrays (X, y) for sklearn metrics and CV.

        Parameters
        ----------
        split        : str 'train', 'val', or 'test'
        return_paths : bool, if True, also returns the list of file paths.

        Returns
        -------
        X : np.ndarray  shape (N, 224, 224, 1), float32, range [0, 1]
        y : np.ndarray  shape (N,),  int {0=LPD, 1=PD}
        paths (optional) : list of str
        """
        split = split.lower().strip()
        df_map = {"train": self._train_df, "val": self._val_df, "test": self._test_df}

        if split not in df_map:
            raise ValueError(f"split must be one of: {list(df_map.keys())}")

        df = df_map[split]
        paths = df["image_path"].astype(str).tolist()
        y = df["label"].astype(int).to_numpy()

        xs = []
        for p in paths:
            img = _load_image(tf.constant(p))
            xs.append(img.numpy())

        X = np.stack(xs, axis=0).astype("float32")

        if return_paths:
            return X, y, paths
        return X, y

    def get_class_weights(self) -> dict:
        """
        Compute balanced class weights from the training manifest.
        Accounts for PD/LPD imbalance, including augmented samples.

        Returns
        -------
        dict  {0: w_lpd, 1: w_pd}  for use in model.fit(class_weight=...)
        """
        labels = self._train_df["label"].values
        classes = np.unique(labels)
        weights = compute_class_weight("balanced", classes=classes, y=labels)
        cw = {int(c): float(w) for c, w in zip(classes, weights)}
        print(f"[DataLoader] Class weights: {cw}")
        return cw

    def get_sample_counts(self) -> dict:
        """Return number of images per split (includes augmented in train)."""
        return {
            "train": len(self._train_df),
            "val": len(self._val_df),
            "test": len(self._test_df),
        }

    def validate_no_leakage(self):
        """
        Assert zero filename collisions across train/val/test.
        Raises AssertionError immediately if leakage is detected.
        """

        def _basenames(df):
            return set(df["image_path"].apply(os.path.basename))

        train_b = _basenames(self._train_df)
        val_b = _basenames(self._val_df)
        test_b = _basenames(self._test_df)

        collisions = (train_b & val_b) | (train_b & test_b) | (val_b & test_b)
        assert len(collisions) == 0, (
            f"DATA LEAKAGE DETECTED — {len(collisions)} filename collision(s) "
            f"across splits: {list(collisions)[:10]}"
        )
        print("[DataLoader] ✓ Zero data leakage verified across all splits.")


# ─────────────────────────────────────────────────────────────────────────────
# Smoke test  (python data_loader.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader = DataLoader()
    print(f"Split counts: {loader.get_sample_counts()}")
    loader.validate_no_leakage()
    loader.get_class_weights()

    for split_name, ds in [
        ("train", loader.get_train_dataset()),
        ("val", loader.get_val_dataset()),
        ("test", loader.get_test_dataset()),
    ]:
        for batch_imgs, batch_labels in ds.take(1):
            shape = batch_imgs.shape
            pmin = float(tf.reduce_min(batch_imgs))
            pmax = float(tf.reduce_max(batch_imgs))
            print(
                f"[{split_name:5s}] shape={shape} | "
                f"dtype={batch_imgs.dtype} | "
                f"pixel=[{pmin:.3f}, {pmax:.3f}]"
            )
            assert shape[1:] == (224, 224, 1)
            assert batch_imgs.dtype == tf.float32
            assert pmin >= 0.0 and pmax <= 1.0

    print("✓ All DataLoader assertions passed.")

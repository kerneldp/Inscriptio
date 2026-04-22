"""
AIKONIC — preprocessing_utils.py
Handles standardizing, augmenting, and building datasets.
Outputs PNGs and manifest CSVs for Phase 2 compatibility.
"""

import os
import cv2
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from scipy.ndimage import gaussian_filter, map_coordinates
import albumentations as A
from tqdm import tqdm
import random
import config


def standardize_and_patch(
    img_path: str, target_size: int = 224, overlap: float = 0.5
) -> list:
    """
    Adaptive patching:
    - Multi-line images use square sliding windows.
    - Single-line images use rectangular chunks letterboxed to fit the target size,
      preserving multiple words for spatial context.
    """
    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not load image: {img_path}")

    _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    if img.mean() < 128:
        img = cv2.bitwise_not(img)

    h, w = img.shape
    image_ar = w / h  # Aspect ratio

    patches = []

    # ---------------------------------------------------------
    # SCENARIO A: Multi-line images (Aspect Ratio <= 2.5)
    # ---------------------------------------------------------
    if image_ar <= 2.5:
        scale = target_size / h
        new_w = int(w * scale)
        resized = cv2.resize(img, (new_w, target_size), interpolation=cv2.INTER_LINEAR)

        step = int(target_size * (1 - overlap))

        if new_w <= target_size:
            canvas = np.full((target_size, target_size), 255, dtype=np.uint8)
            offset_x = (target_size - new_w) // 2
            canvas[:, offset_x : offset_x + new_w] = resized
            patches.append(canvas)
        else:
            for x in range(0, new_w - target_size + 1, step):
                patches.append(resized[:, x : x + target_size])
            if (new_w - target_size) % step != 0:
                patches.append(resized[:, new_w - target_size : new_w])

    # ---------------------------------------------------------
    # SCENARIO B: Single-line images (Aspect Ratio > 2.5)
    # ---------------------------------------------------------
    else:
        # Define a chunk width that captures roughly 3-4 words (e.g., 3x the height)
        chunk_w = int(h * 3.0)
        step = int(chunk_w * (1 - overlap))

        # Slide a rectangular window across the original image
        for x in range(0, w - chunk_w + 1, step):
            crop = img[:, x : x + chunk_w]

            # Letterbox the 1:3 rectangular crop into the 224x224 square
            scale = target_size / chunk_w
            new_h = int(h * scale)
            resized_crop = cv2.resize(
                crop, (target_size, new_h), interpolation=cv2.INTER_LINEAR
            )

            canvas = np.full((target_size, target_size), 255, dtype=np.uint8)
            offset_y = (target_size - new_h) // 2
            canvas[offset_y : offset_y + new_h, :] = resized_crop
            patches.append(canvas)

        # Handle the final trailing piece of the sentence
        if (w - chunk_w) % step != 0 and w > chunk_w:
            crop = img[:, w - chunk_w : w]
            scale = target_size / chunk_w
            new_h = int(h * scale)
            resized_crop = cv2.resize(
                crop, (target_size, new_h), interpolation=cv2.INTER_LINEAR
            )

            canvas = np.full((target_size, target_size), 255, dtype=np.uint8)
            offset_y = (target_size - new_h) // 2
            canvas[offset_y : offset_y + new_h, :] = resized_crop
            patches.append(canvas)

    return patches


def tier1_geometric(img: np.ndarray) -> np.ndarray:
    transform = A.Compose(
        [
            A.ShiftScaleRotate(
                shift_limit=0.10,
                scale_limit=0.05,
                rotate_limit=5,
                border_mode=cv2.BORDER_CONSTANT,
                value=255,
                p=1.0,
            ),
        ]
    )
    return transform(image=img)["image"]


def tier2_elastic(img: np.ndarray, alpha: float, sigma_normalized: float) -> np.ndarray:
    h, w = img.shape[:2]
    sigma = sigma_normalized * w
    dx = gaussian_filter((np.random.rand(h, w) * 2 - 1), sigma=sigma) * alpha
    dy = gaussian_filter((np.random.rand(h, w) * 2 - 1), sigma=sigma) * alpha
    x, y = np.meshgrid(np.arange(w), np.arange(h))
    indices = (np.clip(y + dy, 0, h - 1).ravel(), np.clip(x + dx, 0, w - 1).ravel())
    distorted = map_coordinates(
        img, indices, order=1, mode="constant", cval=255.0
    ).reshape(h, w)
    return np.clip(distorted, 0, 255).astype(np.uint8)


def tier3_photometric(img: np.ndarray) -> np.ndarray:
    transform = A.Compose(
        [
            A.OneOf(
                [
                    A.GaussNoise(
                        var_limit=(1.0, 3.0), p=1.0
                    ),  # Barely visible scanner dust
                    A.GaussianBlur(blur_limit=(3, 3), p=1.0),  # Mild out-of-focus blur
                ],
                p=0.5,
            ),
        ]
    )
    return transform(image=img)["image"]


def augment_image(img: np.ndarray) -> np.ndarray:
    tiers = list(config.TIER_WEIGHTS.keys())
    weights = list(config.TIER_WEIGHTS.values())
    chosen = random.choices(tiers, weights=weights, k=1)[0]

    if chosen == "tier1":
        return tier1_geometric(img)
    elif chosen == "tier2":
        return tier2_elastic(img, config.ELASTIC_ALPHA, config.ELASTIC_SIGMA)
    elif chosen == "tier3":
        return tier3_photometric(img)
    return img


def build_dataset_and_manifests():
    """Builds dataset handling multiple patches per raw image."""
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    config.MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

    manifest_data = {"train": [], "val": [], "test": []}

    for label_idx, cls in enumerate(config.CLASSES):
        cls_dir = config.RAW_DIR / cls
        image_paths = sorted(
            [
                str(p)
                for p in cls_dir.iterdir()
                if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp"]
            ]
        )

        train_val, test = train_test_split(
            image_paths,
            test_size=config.SPLIT_TEST_SIZE,
            random_state=config.RANDOM_SEED,
        )
        train, val = train_test_split(
            train_val,
            test_size=config.SPLIT_VAL_SIZE / (1 - config.SPLIT_TEST_SIZE),
            random_state=config.RANDOM_SEED,
        )

        # Process Val & Test (No Augmentation)
        for split_name, split_paths in [("val", val), ("test", test)]:
            split_dir = config.PROCESSED_DIR / split_name / cls
            split_dir.mkdir(parents=True, exist_ok=True)
            for img_path in split_paths:
                patches = standardize_and_patch(img_path, config.IMAGE_SIZE[0])
                for p_idx, patch in enumerate(patches):
                    out_path = split_dir / f"{Path(img_path).stem}_p{p_idx}_std.png"
                    cv2.imwrite(str(out_path), patch)
                    manifest_data[split_name].append(
                        {
                            "image_path": str(out_path.resolve()),
                            "label": label_idx,
                            "augmented": False,
                        }
                    )

        # Process Train (Standardize + Augment)
        train_dir = config.PROCESSED_DIR / "train" / cls
        train_dir.mkdir(parents=True, exist_ok=True)
        standardized_train = []

        for img_path in train:
            patches = standardize_and_patch(img_path, config.IMAGE_SIZE[0])
            for p_idx, patch in enumerate(patches):
                out_path = train_dir / f"{Path(img_path).stem}_p{p_idx}_std.png"
                cv2.imwrite(str(out_path), patch)
                manifest_data["train"].append(
                    {
                        "image_path": str(out_path.resolve()),
                        "label": label_idx,
                        "augmented": False,
                    }
                )
                standardized_train.append(patch)

        # Augmentation Loop
        current_count = len(standardized_train)
        needed = config.AUGMENT_TARGET - current_count

        for i in tqdm(range(max(0, needed)), desc=f"Augmenting train/{cls}"):
            source_img = standardized_train[i % len(standardized_train)]
            aug_img = augment_image(source_img)
            out_path = train_dir / f"aug_{i:05d}.png"
            cv2.imwrite(str(out_path), aug_img)
            manifest_data["train"].append(
                {
                    "image_path": str(out_path.resolve()),
                    "label": label_idx,
                    "augmented": True,
                }
            )

    # Save Manifests
    pd.DataFrame(manifest_data["train"]).to_csv(config.TRAIN_MANIFEST, index=False)
    pd.DataFrame(manifest_data["val"]).to_csv(config.VAL_MANIFEST, index=False)
    pd.DataFrame(manifest_data["test"]).to_csv(config.TEST_MANIFEST, index=False)
    print("✓ Dataset and Manifests built successfully.")

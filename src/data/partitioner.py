import os
import shutil
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedShuffleSplit

MENDELEY_PATH = "data/raw/mendeley/DATASET DYSGRAPHIA HANDWRITING"
OUTPUT_PATH   = "data/processed/mendeley"
REPORT_DIR    = "reports"
RANDOM_STATE  = 42

LABEL_MAP = {
    "Potential Dysgraphia":     "pd",
    "Low Potential Dysgraphia": "lpd"
}

VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
EXCLUDED_FILES   = {"LPD (10).jpg"}  # flagged in audit — too narrow

# ══════════════════════════════════════════════════════════════════════════════
# 1. COLLECT ALL IMAGES
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("STRATIFIED DATASET PARTITIONING")
print("=" * 60)

filepaths = []
labels    = []

for folder, label in LABEL_MAP.items():
    folder_dir = os.path.join(MENDELEY_PATH, folder)
    if not os.path.isdir(folder_dir):
        continue

    for fname in os.listdir(folder_dir):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in VALID_EXTENSIONS:
            continue
        if fname in EXCLUDED_FILES:
            print(f"  ⚠ Skipping excluded file: {fname}")
            continue

        filepaths.append(os.path.join(folder_dir, fname))
        labels.append(label)

filepaths = np.array(filepaths)
labels    = np.array(labels)

total = len(filepaths)
print(f"\nTotal images loaded: {total}")
print(f"  pd:  {(labels == 'pd').sum()}")
print(f"  lpd: {(labels == 'lpd').sum()}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. STRATIFIED SPLIT — 50:25:25
# ══════════════════════════════════════════════════════════════════════════════

# First split: 50% train, 50% temp
sss1 = StratifiedShuffleSplit(n_splits=1, test_size=0.50, random_state=RANDOM_STATE)
train_idx, temp_idx = next(sss1.split(filepaths, labels))

# Second split: 50% temp → 50% val, 50% test (= 25:25 of total)
sss2 = StratifiedShuffleSplit(n_splits=1, test_size=0.50, random_state=RANDOM_STATE)
val_idx, test_idx = next(sss2.split(filepaths[temp_idx], labels[temp_idx]))

val_idx  = temp_idx[val_idx]
test_idx = temp_idx[test_idx]

splits = {
    "train": train_idx,
    "val":   val_idx,
    "test":  test_idx
}

print(f"\nSplit sizes:")
print(f"  train: {len(train_idx)}")
print(f"  val:   {len(val_idx)}")
print(f"  test:  {len(test_idx)}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. VERIFY ±2% RATIO
# ══════════════════════════════════════════════════════════════════════════════
print(f"\nRatio verification (PD%):")
original_ratio = (labels == "pd").mean() * 100
print(f"  Original:  {original_ratio:.1f}%")

all_within = True
for split_name, idx in splits.items():
    split_labels = labels[idx]
    pd_ratio     = (split_labels == "pd").mean() * 100
    diff         = abs(pd_ratio - original_ratio)
    status       = "✓" if diff <= 2.0 else "✗"
    print(f"  {split_name}:     {pd_ratio:.1f}%  (diff: {diff:.1f}%)  {status}")
    if diff > 2.0:
        all_within = False

if all_within:
    print("✓ All splits within ±2% of original ratio")
else:
    print("✗ Some splits exceed ±2% — consider adjusting random_state")


# ══════════════════════════════════════════════════════════════════════════════
# 4. CREATE FOLDERS AND COPY IMAGES
# ══════════════════════════════════════════════════════════════════════════════
print(f"\nCopying images to {OUTPUT_PATH}...")

# Create all folders
for split_name in splits:
    for label in LABEL_MAP.values():
        folder = os.path.join(OUTPUT_PATH, split_name, label)
        os.makedirs(folder, exist_ok=True)

# Copy images
copy_log = []
for split_name, idx in splits.items():
    for fpath, label in zip(filepaths[idx], labels[idx]):
        fname   = os.path.basename(fpath)
        dst_dir = os.path.join(OUTPUT_PATH, split_name, label)
        dst     = os.path.join(dst_dir, fname)
        shutil.copy2(fpath, dst)
        copy_log.append({
            "filename": fname,
            "label":    label,
            "split":    split_name
        })

print(f"✓ Done! {len(copy_log)} images copied")


# ══════════════════════════════════════════════════════════════════════════════
# 5. FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PARTITION SUMMARY")
print("=" * 60)

summary_rows = []
for split_name, idx in splits.items():
    split_labels = labels[idx]
    pd_count     = (split_labels == "pd").sum()
    lpd_count    = (split_labels == "lpd").sum()
    pd_ratio     = (split_labels == "pd").mean() * 100
    diff         = abs(pd_ratio - original_ratio)

    print(f"\n  {split_name}:")
    print(f"    pd:    {pd_count}")
    print(f"    lpd:   {lpd_count}")
    print(f"    total: {len(idx)}")
    print(f"    pd%:   {pd_ratio:.1f}%  (diff: {diff:.1f}%)  {'✓' if diff <= 2.0 else '✗'}")

    summary_rows.append({
        "split":                    split_name,
        "pd":                       pd_count,
        "lpd":                      lpd_count,
        "total":                    len(idx),
        "pd_ratio_%":               round(pd_ratio, 1),
        "diff_from_original_%":     round(diff, 1),
        "within_2%":                "✓" if diff <= 2.0 else "✗"
    })

# Save logs
copy_df    = pd.DataFrame(copy_log)
summary_df = pd.DataFrame(summary_rows)

copy_df.to_csv(f"{REPORT_DIR}/partition_log.csv", index=False)
summary_df.to_csv(f"{REPORT_DIR}/partition_summary.csv", index=False)

print(f"\n✓ Partition log saved     → {REPORT_DIR}/partition_log.csv")
print(f"✓ Partition summary saved → {REPORT_DIR}/partition_summary.csv")
print("=" * 60)
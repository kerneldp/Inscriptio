import os
import numpy as np
import pandas as pd
from PIL import Image
from collections import Counter

MENDELEY_PATH = "data/raw/mendeley/DATASET DYSGRAPHIA HANDWRITING"
REPORT_DIR    = "reports"

os.makedirs(REPORT_DIR, exist_ok=True)
removal_log = []

# ══════════════════════════════════════════════════════════════════════════════
# 1. MENDELEY DPI SCAN — all 249 images
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("MENDELEY DPI SCAN")
print("=" * 60)

VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
dpi_flagged      = []
label_counts     = Counter()

for label in os.listdir(MENDELEY_PATH):
    label_dir = os.path.join(MENDELEY_PATH, label)
    if not os.path.isdir(label_dir):
        continue

    for fname in os.listdir(label_dir):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in VALID_EXTENSIONS:
            continue

        label_counts[label] += 1
        fpath = os.path.join(label_dir, fname)

        try:
            img = Image.open(fpath)
            dpi = img.info.get("dpi", (0, 0))

            if dpi[0] == 0:
                dpi_flagged.append((fname, label, "no DPI metadata"))

            elif dpi[0] < 200:
                dpi_flagged.append((fname, label, f"low DPI: {dpi[0]}"))

        except Exception as e:
            dpi_flagged.append((fname, label, f"could not open: {e}"))

total_images = sum(label_counts.values())
print(f"Total images scanned:  {total_images}")
print(f"Low DPI (<200) flags:  {len(dpi_flagged)}")

if len(dpi_flagged) == total_images:
    print(f"  ⚠ NOTE: ALL Mendeley images flagged — dataset-wide limitation")
else:
    for fname, label, reason in dpi_flagged:
        print(f"  [{label}] {fname}: {reason}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. MENDELEY VISUAL INSPECTION — all 249 images
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MENDELEY VISUAL INSPECTION — ALL 249 IMAGES")
print("=" * 60)

visual_flagged = []

for label in os.listdir(MENDELEY_PATH):
    label_dir = os.path.join(MENDELEY_PATH, label)
    if not os.path.isdir(label_dir):
        continue

    for fname in os.listdir(label_dir):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in VALID_EXTENSIONS:
            continue

        fpath  = os.path.join(label_dir, fname)
        issues = []

        try:
            img  = Image.open(fpath)
            w, h = img.size
            arr  = np.array(img.convert("L"))

            # Corrupted
            if arr.std() < 5:
                issues.append("blank or corrupted")

            # Blurry
            elif arr.std() < 15:
                issues.append("possibly blurry or low contrast")

            # Too narrow
            if w < 400:
                issues.append(f"too narrow: {w}px")

            # Too short
            if h < 30:
                issues.append(f"too short: {h}px")

        except Exception as e:
            issues.append(f"could not open: {e}")

        if issues:
            visual_flagged.append((fname, label, issues))
            removal_log.append({
                "filename": fname,
                "dataset":  "Mendeley",
                "reason":   "; ".join(issues)
            })

ok = total_images - len(visual_flagged)
print(f"Total images inspected: {total_images}")
print(f"✓ OK:      {ok}")
print(f"✗ Flagged: {len(visual_flagged)}")

if visual_flagged:
    print("\n--- Flagged files ---")
    for fname, label, issues in visual_flagged:
        print(f"  [{label}] {fname}: {'; '.join(issues)}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. MENDELEY LABEL CROSS-CHECK
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MENDELEY LABEL CROSS-CHECK")
print("=" * 60)

VALID_LABELS = {"potential_dysgraphia", "low_potential_dysgraphia"}
found_labels = set(
    l.lower().replace(" ", "_")
    for l in os.listdir(MENDELEY_PATH)
    if os.path.isdir(os.path.join(MENDELEY_PATH, l))
)

unexpected = found_labels - VALID_LABELS
missing    = VALID_LABELS - found_labels

print(f"Expected labels: {sorted(VALID_LABELS)}")
print(f"Found labels:    {sorted(found_labels)}")

if not unexpected and not missing:
    print("✓ Labels match PDM annotation keys exactly")
else:
    if unexpected:
        print(f"✗ Unexpected labels: {unexpected}")
    if missing:
        print(f"✗ Missing labels:    {missing}")

print(f"\nSamples per class:")
for label, count in sorted(label_counts.items()):
    print(f"  {label}: {count}")

# Class imbalance
counts     = list(label_counts.values())
if len(counts) == 2:
    majority  = max(counts)
    minority  = min(counts)
    ratio     = majority / minority
    maj_label = max(label_counts, key=label_counts.get)
    min_label = min(label_counts, key=label_counts.get)
    print(f"\nClass imbalance ratio:")
    print(f"  {maj_label}: {majority}")
    print(f"  {min_label}: {minority}")
    print(f"  Ratio: {ratio:.2f}:1  ", end="")
    if ratio < 1.5:
        print("✓ Roughly balanced")
    elif ratio < 2.0:
        print("⚠ Mild imbalance — consider monitoring")
    else:
        print("✗ Significant imbalance — consider oversampling/weighting")


# ══════════════════════════════════════════════════════════════════════════════
# 4. REMOVAL LOG
# ══════════════════════════════════════════════════════════════════════════════
removal_df = pd.DataFrame(removal_log, columns=["filename", "dataset", "reason"])
removal_df.to_csv(f"{REPORT_DIR}/removal.csv", index=False)

print("\n" + "=" * 60)
print(f"REMOVAL LOG saved → {REPORT_DIR}/removal.csv")
print(f"Total flagged entries: {len(removal_log)}")
print("=" * 60)
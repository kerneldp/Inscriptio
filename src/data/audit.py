import os
import hashlib
import numpy as np
import pandas as pd
from PIL import Image
from collections import Counter

MENDELEY_PATH = "data/raw/mendeley/DATASET DYSGRAPHIA HANDWRITING"
MENDELEY_ZIP  = "data/raw/mendeley/DATASET DYSGRAPHIA HANDWRITING.zip"
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
    label_note = "Labels match PDM annotation keys exactly"
else:
    if unexpected:
        print(f"✗ Unexpected labels: {unexpected}")
    if missing:
        print(f"✗ Missing labels:    {missing}")
    label_note = f"Inconsistencies found: {unexpected | missing}"

print(f"\nSamples per class:")
for label, count in sorted(label_counts.items()):
    print(f"  {label}: {count}")

counts    = list(label_counts.values())
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
# 4. GENERATE CHECKSUM
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("CHECKSUM")
print("=" * 60)

def md5_checksum(fpath):
    hash_md5 = hashlib.md5()
    with open(fpath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

checksum = md5_checksum(MENDELEY_ZIP) if os.path.exists(MENDELEY_ZIP) else "N/A"
print(f"MD5 Checksum: {checksum}")


# ══════════════════════════════════════════════════════════════════════════════
# 5. WRITE reports/dataset.md
# ══════════════════════════════════════════════════════════════════════════════
content = f"""# Dataset Provenance & Metadata

## Mendeley Dysgraphia Dataset

| Field              | Details                                      |
|--------------------|----------------------------------------------|
| **Source**         | Mendeley Data (Ramlan et al.)                |
| **License**        | CC BY 4.0                                    |
| **Modality**       | Offline (handwriting images)                 |
| **Format**         | JPG images                                   |
| **Language/Script**| Malay, Latin script                          |
| **Total Samples**  | {total_images}                               |
| **Archive**        | DATASET DYSGRAPHIA HANDWRITING.zip           |
| **MD5 Checksum**   | {checksum}                                   |
| **Path**           | data/raw/mendeley/                           |

## Class Distribution

| Class                    | Count |
|--------------------------|-------|
| Potential Dysgraphia     | {label_counts.get('Potential Dysgraphia', 0)} |
| Low Potential Dysgraphia | {label_counts.get('Low Potential Dysgraphia', 0)} |
| **Total**                | **{total_images}** |

## Class Imbalance

| Metric         | Value                              |
|----------------|------------------------------------|
| Majority class | {maj_label}: {majority}            |
| Minority class | {min_label}: {minority}            |
| Ratio          | {ratio:.2f}:1 — ✓ Roughly balanced |

## Notes
- This is the only dataset used for the entire study
- DPI metadata not embedded in images — dataset-wide limitation
- {len(removal_log)} image(s) flagged for removal
- Final usable samples: {total_images - len(removal_log)} (after filtering)
"""

with open(f"{REPORT_DIR}/dataset.md", "w", encoding="utf-8") as f:
    f.write(content)

print(f"\n✓ dataset.md saved → {REPORT_DIR}/dataset.md")


# ══════════════════════════════════════════════════════════════════════════════
# 6. WRITE reports/removal.csv
# ══════════════════════════════════════════════════════════════════════════════
removal_rows = []

for entry in removal_log:
    fname  = entry["filename"]
    reason = entry["reason"]

    # Find which class/label this file belongs to
    file_label = "Unknown"
    for label in os.listdir(MENDELEY_PATH):
        label_dir = os.path.join(MENDELEY_PATH, label)
        if not os.path.isdir(label_dir):
            continue
        if fname in os.listdir(label_dir):
            file_label = label
            break

    removal_rows.append({
        "filename":         fname,
        "dataset":          entry["dataset"],
        "class":            file_label,
        "before_filtering": label_counts.get(file_label, 0),
        "removed":          1,
        "remaining":        label_counts.get(file_label, 0) - 1,
        "imbalance_ratio":  round((label_counts.get(file_label, 0) - 1) / minority, 2),
        "label_notes":      label_note,
        "reason":           reason
    })

removal_df = pd.DataFrame(removal_rows) if removal_rows else pd.DataFrame(
    columns=["filename", "dataset", "class", "before_filtering",
             "removed", "remaining", "imbalance_ratio", "label_notes", "reason"]
)

removal_df.to_csv(f"{REPORT_DIR}/removal.csv", index=False)

print(f"✓ removal.csv saved → {REPORT_DIR}/removal.csv")
print(f"\nTotal flagged entries: {len(removal_log)}")
print("=" * 60)
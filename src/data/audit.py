import os
import gzip
import numpy as np
import pandas as pd
import random
from PIL import Image
from collections import Counter

DROTAR_CSV    = "data/raw/drotar/dataSciRep_Public.csv"
MENDELEY_PATH = "data/raw/mendeley/DATASET DYSGRAPHIA HANDWRITING"
EMNIST_PATH   = "data/raw/emnist/gzip"
KAGGLE_PATH   = "data/raw/kaggle/dataset"
REPORT_DIR    = "reports"

os.makedirs(REPORT_DIR, exist_ok=True)
removal_log = []

# ══════════════════════════════════════════════════════════════════════════════
# 1. DROTÁR & DOBEŠ
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("DROTÁR & DOBEŠ AUDIT")
print("=" * 60)

REQUIRED_COLS     = ["x", "y", "pressure", "azimuth", "altitude"]
EXPECTED_SUBJECTS = 120

df = pd.read_csv(DROTAR_CSV)

missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
if missing_cols:
    print(f"✗ CRITICAL — missing columns: {missing_cols}")
else:
    print(f"✓ All 5 signal columns present")

drotar_results = []
for user_id, group in df.groupby("user_id"):
    rows   = len(group)
    issues = []

    for col in REQUIRED_COLS:
        nulls = group[col].isnull().sum()
        if nulls > 0:
            issues.append(f"{col} has {nulls} nulls")

    if rows < 10:
        issues.append(f"only {rows} rows — possible truncation")

    status = "OK" if not issues else "ISSUES: " + "; ".join(issues)
    drotar_results.append({"user_id": user_id, "rows": rows, "status": status})

    if status != "OK":
        removal_log.append({
            "filename": f"user_{user_id}",
            "dataset":  "Drotar",
            "reason":   status
        })

ok     = [r for r in drotar_results if r["status"] == "OK"]
issues = [r for r in drotar_results if r["status"] != "OK"]

print(f"Total subjects found: {len(drotar_results)}")
print(f"Expected:             {EXPECTED_SUBJECTS}  {'✓' if len(drotar_results) == EXPECTED_SUBJECTS else '✗ MISMATCH'}")
print(f"✓ OK:      {len(ok)}")
print(f"✗ Issues:  {len(issues)}")

if issues:
    print("\n--- Problem subjects ---")
    for r in issues:
        print(f"  user_{r['user_id']} ({r['rows']} rows): {r['status']}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. MENDELEY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MENDELEY AUDIT")
print("=" * 60)

mendeley_results  = []
label_file_counts = Counter()

for label in os.listdir(MENDELEY_PATH):
    label_dir = os.path.join(MENDELEY_PATH, label)
    if not os.path.isdir(label_dir):
        continue

    for fname in os.listdir(label_dir):
        if not fname.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff")):
            continue

        fpath  = os.path.join(label_dir, fname)
        issues = []

        try:
            img  = Image.open(fpath)
            w, h = img.size

            if w < 400:
                issues.append(f"too narrow: {w}px wide")
            if h < 30:
                issues.append(f"too short: {h}px tall")

            arr = np.array(img.convert("L"))
            if arr.std() < 5:
                issues.append("blank or corrupted")

        except Exception as e:
            issues.append(f"could not open: {e}")

        status = "OK" if not issues else "FLAG: " + "; ".join(issues)
        mendeley_results.append({"file": fname, "label": label, "status": status})
        label_file_counts[label] += 1

        if status != "OK":
            removal_log.append({
                "filename": fname,
                "dataset":  "Mendeley",
                "reason":   status
            })

ok      = [r for r in mendeley_results if r["status"] == "OK"]
flagged = [r for r in mendeley_results if r["status"] != "OK"]

print(f"Total images scanned: {len(mendeley_results)}")
print(f"✓ OK:      {len(ok)}")
print(f"✗ Flagged: {len(flagged)}")

print(f"\nSamples per class:")
for label, count in sorted(label_file_counts.items()):
    print(f"  {label}: {count}")

if flagged:
    print(f"\n--- Flagged files ---")
    for r in flagged:
        print(f"  [{r['label']}] {r['file']}: {r['status']}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. EMNIST BALANCED
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("EMNIST BALANCED AUDIT")
print("=" * 60)

def load_images(path):
    with gzip.open(path, 'rb') as f:
        f.read(4)
        num  = int.from_bytes(f.read(4), 'big')
        rows = int.from_bytes(f.read(4), 'big')
        cols = int.from_bytes(f.read(4), 'big')
        data = np.frombuffer(f.read(), dtype=np.uint8)
        return data.reshape(num, rows, cols), rows, cols

def load_labels(path):
    with gzip.open(path, 'rb') as f:
        f.read(4)
        num = int.from_bytes(f.read(4), 'big')
        return np.frombuffer(f.read(), dtype=np.uint8)

train_imgs, rows, cols = load_images(f"{EMNIST_PATH}/emnist-balanced-train-images-idx3-ubyte.gz")
train_lbls             = load_labels(f"{EMNIST_PATH}/emnist-balanced-train-labels-idx1-ubyte.gz")
test_imgs,  _,    _    = load_images(f"{EMNIST_PATH}/emnist-balanced-test-images-idx3-ubyte.gz")
test_lbls              = load_labels(f"{EMNIST_PATH}/emnist-balanced-test-labels-idx1-ubyte.gz")

all_lbls       = np.concatenate([train_lbls, test_lbls])
unique_classes = np.unique(all_lbls)
emnist_counts  = [np.sum(train_lbls == c) for c in unique_classes]

print(f"Resolution:     {rows}x{cols}  {'✓' if rows == 28 and cols == 28 else '✗ EXPECTED 28x28'}")
print(f"Train samples:  {len(train_imgs)}")
print(f"Test samples:   {len(test_imgs)}")
print(f"Total samples:  {len(train_imgs) + len(test_imgs)}")
print(f"Classes:        {len(unique_classes)}  {'✓' if len(unique_classes) == 47 else '✗ EXPECTED 47'}")
print(f"Balance:        min={min(emnist_counts)}  max={max(emnist_counts)}  "
      f"{'✓ Balanced' if max(emnist_counts) - min(emnist_counts) <= 10 else '⚠ Imbalanced'}")

blank = sum(1 for img in train_imgs[:1000] if img.std() < 5)
print(f"Blank/corrupt (sampled 1000 train): {blank}")

# ══════════════════════════════════════════════════════════════════════════════
# DPI + VISUAL 10% INSPECTION (Mendeley & Kaggle)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("DPI + VISUAL 10% INSPECTION")
print("=" * 60)

def audit_image_quality(fpath):
    issues = []
    try:
        img = Image.open(fpath)
        arr = np.array(img.convert("L"))

        # Corrupted check first
        if arr.std() < 5:
            issues.append("blank or corrupted")
            return issues

        # Blurry check
        if arr.std() < 15:
            issues.append("possibly blurry or low contrast")

        # Shadowed check
        if arr.mean() < 20:
            issues.append("possibly shadowed or too dark")

    except Exception as e:
        issues.append(f"could not open: {e}")

    return issues


def collect_images(base_path):
    all_images = []
    for root, dirs, files in os.walk(base_path):
        for fname in files:
            if fname.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff")):
                all_images.append(os.path.join(root, fname))
    return all_images


for dataset_name, dataset_path in [("Mendeley", MENDELEY_PATH), ("Kaggle", KAGGLE_PATH)]:
    print(f"\n--- {dataset_name} ---")
    all_images = collect_images(dataset_path)

    # ── Task 1: Scan ALL images for DPI below 200 ──
    dpi_flagged = []
    for fpath in all_images:
        try:
            img = Image.open(fpath)
            dpi = img.info.get("dpi", (0, 0))

            if dpi[0] == 0:
                dpi_flagged.append((os.path.basename(fpath), "no DPI metadata"))
                removal_log.append({
                    "filename": os.path.basename(fpath),
                    "dataset":  dataset_name,
                    "reason":   "no DPI metadata"
                })
            elif dpi[0] < 200:
                dpi_flagged.append((os.path.basename(fpath), dpi[0]))
                removal_log.append({
                    "filename": os.path.basename(fpath),
                    "dataset":  dataset_name,
                    "reason":   f"low DPI: {dpi[0]}"
                })
        except:
            pass

    # ── Task 2: Visually inspect random 10% sample ──
    sample_size    = max(1, int(len(all_images) * 0.1))
    sample         = random.sample(all_images, sample_size)
    visual_flagged = []

    for fpath in sample:
        issues = audit_image_quality(fpath)
        if issues:
            visual_flagged.append((os.path.basename(fpath), issues))
            removal_log.append({
                "filename": os.path.basename(fpath),
                "dataset":  dataset_name,
                "reason":   "; ".join(issues)
            })

    # ── Summary ──
    print(f"Total images:          {len(all_images)}")
    print(f"Low DPI (<200) flags:  {len(dpi_flagged)}")

    if len(dpi_flagged) == len(all_images):
        print(f"  ⚠ NOTE: ALL {dataset_name} images flagged — dataset-wide limitation")
    else:
        for fname, dpi in dpi_flagged[:10]:  # show first 10 only
            print(f"    {fname}: {dpi} DPI")
        if len(dpi_flagged) > 10:
            print(f"    ... and {len(dpi_flagged) - 10} more")

    print(f"10% sample inspected:  {sample_size}")
    print(f"Visual flags:          {len(visual_flagged)}")

    if visual_flagged:
        print(f"\n  Visual inspection flags:")
        for fname, issues in visual_flagged:
            print(f"    {fname}: {'; '.join(issues)}")

# ══════════════════════════════════════════════════════════════════════════════
# 4. KAGGLE DYSGRAPHIA
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("KAGGLE DYSGRAPHIA AUDIT")
print("=" * 60)

EXPECTED_KAGGLE = {
    "corrected":      462,
    "high potential": 435,
    "low potential":  417
}

kaggle_results   = []
kaggle_counts    = Counter()
VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}

for severity in os.listdir(KAGGLE_PATH):
    severity_dir = os.path.join(KAGGLE_PATH, severity)
    if not os.path.isdir(severity_dir):
        continue

    for fname in os.listdir(severity_dir):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in VALID_EXTENSIONS:
            continue

        fpath  = os.path.join(severity_dir, fname)
        issues = []

        try:
            img  = Image.open(fpath)
            w, h = img.size
            arr  = np.array(img.convert("L"))

            if arr.std() < 5:
                issues.append("blank or corrupted")
            if w < 100 or h < 100:
                issues.append(f"too small: {w}x{h}")
            if arr.mean() > 245:
                issues.append("possible blank/drawing — near white")
            elif arr.mean() < 10:
                issues.append("possible blank/drawing — near black")

        except Exception as e:
            issues.append(f"could not open: {e}")

        status = "OK" if not issues else "FLAG: " + "; ".join(issues)
        kaggle_results.append({"file": fname, "severity": severity, "status": status})
        kaggle_counts[severity] += 1

        if status != "OK":
            removal_log.append({
                "filename": fname,
                "dataset":  "Kaggle",
                "reason":   status
            })

ok      = [r for r in kaggle_results if r["status"] == "OK"]
flagged = [r for r in kaggle_results if r["status"] != "OK"]

print(f"Total images scanned: {len(kaggle_results)}")
print(f"✓ OK:      {len(ok)}")
print(f"✗ Flagged: {len(flagged)}")

print(f"\nSamples per severity folder:")
for severity, count in sorted(kaggle_counts.items()):
    expected = EXPECTED_KAGGLE.get(severity, "?")
    match    = "✓" if count == expected else f"✗ EXPECTED {expected}"
    print(f"  {severity}: {count} {match}")

print(f"\nTotal: {sum(kaggle_counts.values())}  "
      f"{'✓' if sum(kaggle_counts.values()) == 1314 else '✗ EXPECTED 1314'}")

if flagged:
    print(f"\n--- Flagged files ---")
    for r in flagged:
        print(f"  [{r['severity']}] {r['file']}: {r['status']}")


# ══════════════════════════════════════════════════════════════════════════════
# 5. MENDELEY LABEL CROSS-CHECK + POST-FILTER COUNT
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MENDELEY LABEL CROSS-CHECK")
print("=" * 60)

VALID_LABELS = {"Potential Dysgraphia", "Low Potential Dysgraphia"}
found_labels = set(
    l for l in os.listdir(MENDELEY_PATH)
    if os.path.isdir(os.path.join(MENDELEY_PATH, l))
)

unexpected = found_labels - VALID_LABELS
missing    = VALID_LABELS - found_labels

print(f"Expected labels:  {sorted(VALID_LABELS)}")
print(f"Found labels:     {sorted(found_labels)}")

if not unexpected and not missing:
    print("✓ Labels match PDM annotation keys exactly")
else:
    if unexpected:
        print(f"✗ Unexpected labels: {unexpected}")
    if missing:
        print(f"✗ Missing labels:    {missing}")

print(f"\nFiles per label (before filtering):")
for label, count in sorted(label_file_counts.items()):
    print(f"  {label}: {count}")

print("\n" + "=" * 60)
print("POST-FILTER SAMPLE COUNT & CLASS IMBALANCE")
print("=" * 60)

mendeley_removed = [e["filename"] for e in removal_log if e["dataset"] == "Mendeley"]
print(f"Removed from Mendeley: {len(mendeley_removed)} file(s)")
for f in mendeley_removed:
    print(f"  - {f}")

remaining = {}
for label, total in label_file_counts.items():
    removed_in_class = sum(
        1 for f in mendeley_removed
        if any(f == fname for fname in os.listdir(os.path.join(MENDELEY_PATH, label)))
    )
    remaining[label] = total - removed_in_class

print(f"\nRemaining samples per class (after filtering):")
for label, count in sorted(remaining.items()):
    print(f"  {label}: {count}")
print(f"  Total: {sum(remaining.values())}")

rem_counts = list(remaining.values())
if len(rem_counts) == 2:
    majority  = max(rem_counts)
    minority  = min(rem_counts)
    ratio     = majority / minority
    maj_label = max(remaining, key=remaining.get)
    min_label = min(remaining, key=remaining.get)
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

summary = pd.DataFrame([
    {"label": label, "remaining_samples": count, "imbalance_ratio": round(max(rem_counts)/min(rem_counts), 2)}
    for label, count in sorted(remaining.items())
])
summary.to_csv(f"{REPORT_DIR}/mendeley_class_summary.csv", index=False)
print(f"\nSummary saved → {REPORT_DIR}/mendeley_class_summary.csv")


# ══════════════════════════════════════════════════════════════════════════════
# 6. REMOVAL LOG  ← always last
# ══════════════════════════════════════════════════════════════════════════════
removal_df = pd.DataFrame(removal_log, columns=["filename", "dataset", "reason"])
removal_df.to_csv(f"{REPORT_DIR}/removal_logs.csv", index=False)

print("\n" + "=" * 60)
print(f"REMOVAL LOG saved → {REPORT_DIR}/removal_logs.csv")
print(f"Total flagged entries: {len(removal_log)}")
print("=" * 60)
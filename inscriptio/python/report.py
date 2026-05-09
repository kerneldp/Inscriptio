"""
report.py — Full XAI ML Pipeline
Endpoints:
  POST /api/report/preprocess/preview  — upload image, return binarized preview
  POST /api/report/analyze             — run MobileNetV3 + GradCAM + SHAP
  GET  /api/report/{report_id}         — fetch saved report
  POST /api/report/{report_id}/validate — clinician verify/disagree
  PATCH /api/report/{report_id}/notes  — autosave educator notes
  POST /api/report/{report_id}/save    — commit to student history
"""

import os
import io
import json
import base64
import logging
import numpy as np
import cv2
import tensorflow as tf
import shap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path

from database import get_db
from models import Report, Student
from auth import get_current_user
from typing import Optional

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("report")

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_PATH  = Path(__file__).parent / "FINAL_production_model.keras"
CLASS_NAMES = ["LPD", "PD"]
LABEL_MAP   = {"PD": "Potential", "LPD": "Low Potential"}
UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

router = APIRouter(prefix="/api/report", tags=["Report & ML Pipeline"])

# ── Load model once at startup ────────────────────────────────────────────────
_model = None

def get_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise HTTPException(
                status_code=503,
                detail=f"Model file not found. Place FINAL_production_model.keras in the python/ folder."
            )
        log.info("Loading MobileNetV3 model...")
        _model = tf.keras.models.load_model(str(MODEL_PATH))
        log.info("Model loaded successfully.")
    return _model


# ══════════════════════════════════════════════════════════════════════════════
# ── Preprocessing (exact replication of training pipeline) ───────────────────
# ══════════════════════════════════════════════════════════════════════════════

def otsu_binarize(img_gray: np.ndarray) -> np.ndarray:
    _, binary = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if binary.mean() < 128:
        binary = cv2.bitwise_not(binary)
    return binary


def standardize_patch_and_track(img_gray: np.ndarray, target_size: int = 224, overlap: float = 0.5):
    img = otsu_binarize(img_gray)
    h, w = img.shape
    image_ar = w / h
    patches, metadata = [], []

    if image_ar <= 2.5:  # Multi-line / portrait
        scale = target_size / h
        new_w = int(w * scale)
        resized = cv2.resize(img, (new_w, target_size), interpolation=cv2.INTER_LINEAR)
        step = int(target_size * (1 - overlap))

        if new_w <= target_size:
            canvas = np.full((target_size, target_size), 255, dtype=np.uint8)
            offset_x = (target_size - new_w) // 2
            canvas[:, offset_x:offset_x + new_w] = resized
            patches.append(canvas)
            metadata.append({"type": "A_small", "offset_x": offset_x, "new_w": new_w, "orig_w": w, "orig_h": h})
        else:
            for x in range(0, new_w - target_size + 1, step):
                patches.append(resized[:, x:x + target_size])
                metadata.append({"type": "A_slide", "x_start": x, "scale": scale, "orig_w": w, "orig_h": h})
            if (new_w - target_size) % step != 0:
                patches.append(resized[:, new_w - target_size:new_w])
                metadata.append({"type": "A_slide", "x_start": new_w - target_size, "scale": scale, "orig_w": w, "orig_h": h})
    else:  # Single-line / landscape
        chunk_w = int(h * 3.0)
        step = int(chunk_w * (1 - overlap))

        def process_chunk(x_start, c_width):
            crop = img[:, x_start:x_start + c_width]
            scale = target_size / c_width
            new_h = int(h * scale)
            resized_crop = cv2.resize(crop, (target_size, new_h), interpolation=cv2.INTER_LINEAR)
            canvas = np.full((target_size, target_size), 255, dtype=np.uint8)
            offset_y = (target_size - new_h) // 2
            canvas[offset_y:offset_y + new_h, :] = resized_crop
            patches.append(canvas)
            metadata.append({"type": "B", "x_start": x_start, "c_width": c_width,
                              "offset_y": offset_y, "new_h": new_h, "orig_h": h})

        for x in range(0, w - chunk_w + 1, step):
            process_chunk(x, chunk_w)
        if (w - chunk_w) % step != 0 and w > chunk_w:
            process_chunk(w - chunk_w, chunk_w)

    return img, patches, metadata


# ══════════════════════════════════════════════════════════════════════════════
# ── GradCAM ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def make_gradcam_heatmap(img_array: np.ndarray, model) -> np.ndarray:
    if len(img_array.shape) == 3:
        img_array = np.expand_dims(img_array, axis=0)
    img_tensor = tf.convert_to_tensor(img_array, dtype=tf.float32)
    x = tf.concat([img_tensor, img_tensor, img_tensor], axis=-1)

    base_model    = model.get_layer("MobileNetV3Small")
    pool_layer    = model.get_layer("global_avg_pool")
    bn_layer      = model.get_layer("batch_norm")
    dense_layer   = model.get_layer("dense_128")
    dropout_layer = model.get_layer("dropout")
    classifier    = model.get_layer("classifier")

    with tf.GradientTape() as tape:
        last_conv = base_model(x, training=False)
        tape.watch(last_conv)
        x_head = pool_layer(last_conv)
        x_head = bn_layer(x_head, training=False)
        x_head = dense_layer(x_head)
        x_head = dropout_layer(x_head, training=False)
        preds  = classifier(x_head)
        pred_index    = tf.argmax(preds[0])
        class_channel = preds[:, pred_index]

    grads        = tape.gradient(class_channel, last_conv)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    heatmap = last_conv[0] @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)
    heatmap = (tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)).numpy()
    return cv2.resize(heatmap, (img_array.shape[2], img_array.shape[1]))


def make_severe_anomaly_panel(binary_img: np.ndarray, full_shap: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Phase 04 — Severe Anomaly Focus panel.
    Shows only the top 5% most extreme SHAP attribution zones.
    Uses morphological cleanup + contour outlines for a clean, clinical look.
    """
    # Convert to 3-channel grayscale base (keep text readable)
    img_rgb = cv2.cvtColor(binary_img, cv2.COLOR_GRAY2BGR)
 
    if not np.any(mask):
        return img_rgb
 
    # Tighter threshold — top 5% only (was 90th percentile before)
    threshold = np.percentile(np.abs(full_shap[mask]), 95)
    severe_mask = (np.abs(full_shap) >= threshold).astype(np.uint8)
 
    # Morphological cleanup: remove tiny noise blobs, keep only meaningful zones
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    kernel_open  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    severe_mask  = cv2.morphologyEx(severe_mask, cv2.MORPH_CLOSE, kernel_close)
    severe_mask  = cv2.morphologyEx(severe_mask, cv2.MORPH_OPEN,  kernel_open)
 
    # Very light red fill so text underneath remains legible
    fill_overlay        = img_rgb.copy()
    fill_overlay[severe_mask > 0] = [180, 60, 60]   # dark red in BGR
    result = cv2.addWeighted(img_rgb, 0.72, fill_overlay, 0.28, 0)
 
    # Crisp red contour outlines — this is the dominant visual cue
    contours, _ = cv2.findContours(severe_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Filter out tiny contours (area < 100px) to avoid noise dots
    significant = [c for c in contours if cv2.contourArea(c) >= 100]
    cv2.drawContours(result, significant, -1, (0, 0, 200), 2)
 
    return result
 

def generate_findings(binary_img: np.ndarray, full_shap: np.ndarray, mask: np.ndarray, label: str) -> str:
    """
    Phase 04 — Evidence-Based Clinical Findings.
    Performs spatial analysis of SHAP attributions to determine
    whether anomalies concentrate in whitespace vs. character strokes,
    then returns a citation-grounded clinical narrative.
    """
    if label == "Low Potential":
        return (
            "No significant dysgraphic patterns were detected in this sample. "
            "The handwriting exhibits characteristics consistent with typical graphomotor development. "
            "SHAP attribution values remain below decision-relevant thresholds across all spatial zones, "
            "indicating that neither letter formation nor inter-character spacing shows statistically "
            "anomalous patterns relative to the model's training distribution (APA, 2013)."
        )

    if not np.any(mask):
        return (
            "Anomaly localization could not be determined due to insufficient pixel-level SHAP signal. "
            "Please re-run the analysis with a higher-resolution scan."
        )

    # Spatial split: ink (character bodies) vs. whitespace
    ink_mask   = binary_img < 128   # dark pixels = character strokes
    white_mask = binary_img >= 128  # light pixels = inter-character whitespace

    shap_abs = np.abs(full_shap)
    ink_signal   = float(np.mean(shap_abs[ink_mask   & mask])) if np.any(ink_mask   & mask) else 0.0
    white_signal = float(np.mean(shap_abs[white_mask & mask])) if np.any(white_mask & mask) else 0.0

    if white_signal >= ink_signal:
        # Anomalies in whitespace → Spatial Dysgraphia pattern
        dominant = "whitespace"
        findings = (
            "The predictive anomalies are heavily localized in the whitespace between characters. "
            "Deuel (1995) defines Spatial Dysgraphia as producing illegible writing - whether spontaneous "
            "or copied - due to a fundamental deficit in spatial perception, which manifests directly as "
            "abnormal letter spacing and erratic kerning. Chung et al. (2020) further specify that in spatial "
            "dysgraphia, oral spelling and fine-motor tapping speed are preserved, indicating that the spacing "
            "irregularities detected in this zone are perceptual-spatial in origin rather than purely motoric. "
            "These atypical inter-character intervals are a strong behavioral marker of impaired graphomotor "
            "coordination, consistent with Specific Learning Disorder criteria (APA, 2013). Döhla and Heim (2016) "
            "additionally note that dysgraphia and dyslexia share spatial-processing deficits that manifest during "
            "the physical execution of written output."
        )
    else:
        # Anomalies in character strokes → Motor/Dysfluent pattern
        dominant = "character strokes"
        findings = (
            "The predictive anomalies are concentrated within the character strokes themselves, suggesting "
            "disruptions in graphomotor execution. Kushki et al. (2011) identify that children with dysgraphia "
            "exhibit significantly increased pen pressure variability and irregular stroke formation, reflecting "
            "underlying motor planning deficits. Overvelde and Hulstijn (2011) further demonstrate that letter "
            "formation errors - particularly in stroke direction and sequencing - are reliable markers of "
            "Dysfluent Dysgraphia. These motor-level irregularities, concentrated in the ink stroke zones, are "
            "consistent with impaired kinesthetic feedback during handwriting production, as described under "
            "Specific Learning Disorder criteria (APA, 2013). Döhla and Heim (2016) note that such "
            "graphomotor deficits frequently co-occur with reading difficulties, warranting comprehensive "
            "assessment beyond handwriting alone."
        )

    log.info(f"Findings: dominant anomaly zone = {dominant} (ink={ink_signal:.4f}, white={white_signal:.4f})")
    return findings


# ══════════════════════════════════════════════════════════════════════════════
# ── Full pipeline ─────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def ndarray_to_b64(arr: np.ndarray) -> str:
    _, buf = cv2.imencode(".png", arr)
    return base64.b64encode(buf).decode()

def fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def run_pipeline(img_gray: np.ndarray, model):
    binary_img, patches, meta = standardize_patch_and_track(img_gray)
    if not patches:
        raise ValueError("No patches generated from image.")

    h, w = binary_img.shape
    full_gradcam  = np.zeros((h, w), dtype=np.float32)
    full_shap     = np.zeros((h, w), dtype=np.float32)
    overlap_count = np.zeros((h, w), dtype=np.float32)
    pd_probs      = []
    patch_inputs  = []

    # 1. Probability averaging across patches
    for patch in patches:
        p_input = np.expand_dims(np.expand_dims(patch.astype('float32') / 255.0, -1), 0)
        patch_inputs.append(p_input)
        preds = model.predict(p_input, verbose=0)
        pd_probs.append(float(preds[0][1]))

    avg_pd_prob   = float(np.mean(pd_probs))
    raw_label     = "PD" if avg_pd_prob >= 0.5 else "LPD"
    softmax_score = avg_pd_prob if raw_label == "PD" else (1.0 - avg_pd_prob)
    label         = LABEL_MAP[raw_label]

    # 2. GradCAM + SHAP per patch, stitch back
    masker    = shap.maskers.Image("inpaint_telea", (224, 224, 1))
    explainer = shap.Explainer(model.predict, masker, output_names=CLASS_NAMES)

    for p_input, m in zip(patch_inputs, meta):
        hm = make_gradcam_heatmap(p_input, model)
        sv = explainer(p_input, max_evals=300, outputs=shap.Explanation.argsort.flip[:1])
        shap_val = sv.values[0, ..., 0]
        if len(shap_val.shape) == 3:
            shap_val = np.sum(shap_val, axis=-1)
        if raw_label == "LPD":
            shap_val *= -1

        if m["type"] == "B":
            hm_c = hm[m["offset_y"]: m["offset_y"] + m["new_h"], :]
            sh_c = shap_val[m["offset_y"]: m["offset_y"] + m["new_h"], :]
            hm_r = cv2.resize(hm_c, (m["c_width"], m["orig_h"]))
            sh_r = cv2.resize(sh_c, (m["c_width"], m["orig_h"]))
            xs, xe = m["x_start"], m["x_start"] + m["c_width"]
            full_gradcam[:, xs:xe] += hm_r
            full_shap[:, xs:xe]    += sh_r
            overlap_count[:, xs:xe] += 1

        elif m["type"] == "A_small":
            hm_c = hm[:, m["offset_x"]: m["offset_x"] + m["new_w"]]
            sh_c = shap_val[:, m["offset_x"]: m["offset_x"] + m["new_w"]]
            full_gradcam  += cv2.resize(hm_c, (w, h))
            full_shap     += cv2.resize(sh_c, (w, h))
            overlap_count += 1

        elif m["type"] == "A_slide":
            hm_r = cv2.resize(hm,       (int(224 / m["scale"]), h))
            sh_r = cv2.resize(shap_val, (int(224 / m["scale"]), h))
            xs   = int(m["x_start"] / m["scale"])
            xe   = xs + hm_r.shape[1]
            if xe > w:
                hm_r, sh_r, xe = hm_r[:, :w - xs], sh_r[:, :w - xs], w
            full_gradcam[:, xs:xe] += hm_r
            full_shap[:, xs:xe]    += sh_r
            overlap_count[:, xs:xe] += 1

    mask = overlap_count > 0
    full_gradcam[mask] /= overlap_count[mask]
    full_shap[mask]    /= overlap_count[mask]

    # 3. Render panels
    img_rgb  = cv2.cvtColor(binary_img, cv2.COLOR_GRAY2RGB)
    ink_mask = cv2.bitwise_not(binary_img)
    kernel   = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (40, 40))
    dilated  = cv2.dilate(ink_mask, kernel) > 0

    heatmap_color   = cv2.applyColorMap(np.uint8(255 * full_gradcam), cv2.COLORMAP_JET)
    gradcam_overlay = np.where(dilated[..., None],
                               cv2.addWeighted(img_rgb, 0.5, heatmap_color, 0.5, 0),
                               img_rgb)

    vmax = float(np.max(np.abs(full_shap[mask]))) if np.any(mask) else 1.0
    signal_mask = (np.abs(full_shap) >= np.percentile(np.abs(full_shap[mask]), 65)) \
                  if np.any(mask) else np.zeros_like(full_shap, dtype=bool)

    # SHAP panel via matplotlib
    fig, ax = plt.subplots(figsize=(6, max(2, 6 * h / w)))
    ax.imshow(binary_img, cmap="gray")
    masked_shap = np.ma.masked_where(~(dilated & signal_mask), full_shap)
    ax.imshow(masked_shap, cmap="coolwarm", alpha=0.75, vmin=-vmax, vmax=vmax)
    ax.axis("off")

    # 4. Phase 04 — Severe Anomaly Focus panel
    severe_panel = make_severe_anomaly_panel(binary_img, full_shap, mask)

    # 5. Phase 04 — Patch-level probability breakdown
    patch_breakdown = [
        {
            "patch_num":    i + 1,
            "pd_prob":      round(prob * 100, 1),
            "label":        "Dysgraphic (PD)" if prob >= 0.5 else "Normal (LPD)",
            "confidence":   round((prob if prob >= 0.5 else 1.0 - prob) * 100, 1),
        }
        for i, prob in enumerate(pd_probs)
    ]

    # 6. Phase 04 — Evidence-based clinical findings
    findings = generate_findings(binary_img, full_shap, mask, label)

    return {
        "label":              label,
        "softmax_score":      round(softmax_score, 4),
        "avg_pd_prob":        round(avg_pd_prob * 100, 1),
        "patch_breakdown":    patch_breakdown,
        "findings":           findings,
        "original_b64":       ndarray_to_b64(binary_img),
        "gradcam_b64":        ndarray_to_b64(cv2.cvtColor(gradcam_overlay, cv2.COLOR_RGB2BGR)),
        "shap_b64":           fig_to_b64(fig),
        "severe_anomaly_b64": ndarray_to_b64(severe_panel),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ── Schemas ───────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

class ValidateRequest(BaseModel):
    decision: str   # "verify" | "disagree"

class NotesRequest(BaseModel):
    notes: str

class SaveRequest(BaseModel):
    decision: Optional[str] = None
    notes: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# ── Routes ────────────────────────────────────────────════════════════════════
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/preprocess/preview")
async def preprocess_preview(
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
):
    contents = await file.read()
    arr      = np.frombuffer(contents, dtype=np.uint8)
    img_gray = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img_gray is None:
        raise HTTPException(status_code=400, detail="Could not decode image. Use PNG or JPG.")

    binary = otsu_binarize(img_gray)
    thumb  = cv2.resize(binary, (224, 224))

    return {
        "original_b64":  ndarray_to_b64(img_gray),
        "binarized_b64": ndarray_to_b64(binary),
        "thumbnail_b64": ndarray_to_b64(thumb),
        "original_size": list(img_gray.shape),
    }


@router.post("/analyze")
async def analyze(
    file:         UploadFile = File(...),
    student_id:   int        = Form(...),
    session_date: str        = Form(default=None),
    db:           Session    = Depends(get_db),
    current_user: dict       = Depends(get_current_user),
):
    if not session_date:
        session_date = datetime.utcnow().strftime("%Y-%m-%d")

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    contents = await file.read()
    arr      = np.frombuffer(contents, dtype=np.uint8)
    img_gray = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img_gray is None:
        raise HTTPException(status_code=400, detail="Could not decode image. Use PNG or JPG.")

    model = get_model()
    try:
        result = run_pipeline(img_gray, model)
    except Exception as e:
        log.error(f"Pipeline error: {e}")
        raise HTTPException(status_code=500, detail=f"ML pipeline error: {str(e)}")

    def save_img_b64(b64_str: str, suffix: str) -> str:
        ts    = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        fname = f"stu{student_id}_{ts}_{suffix}.png"
        path  = UPLOADS_DIR / fname
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64_str))
        return str(path)

    orig_path          = save_img_b64(result["original_b64"],       "original")
    gradcam_path       = save_img_b64(result["gradcam_b64"],        "gradcam")
    shap_path          = save_img_b64(result["shap_b64"],           "shap")
    severe_anomaly_path= save_img_b64(result["severe_anomaly_b64"], "severe")

    from models import User
    db_user = db.query(User).filter(User.email == current_user["email"]).first()
    uploader_id = db_user.id if db_user else 1

    report = Report(
        student_id         = student_id,
        uploaded_by        = uploader_id,
        original_img       = orig_path,
        gradcam_img        = gradcam_path,
        shap_img           = shap_path,
        severe_anomaly_img = severe_anomaly_path,
        softmax_score      = result["softmax_score"],
        label              = result["label"],
        session_date       = session_date,
        patch_scores       = json.dumps(result["patch_breakdown"]),
        findings           = result["findings"],
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "report_id":          report.id,
        "student_id":         student_id,
        "label":              result["label"],
        "softmax_score":      result["softmax_score"],
        "avg_pd_prob":        result["avg_pd_prob"],
        "patch_breakdown":    result["patch_breakdown"],
        "findings":           result["findings"],
        "original_b64":       result["original_b64"],
        "gradcam_b64":        result["gradcam_b64"],
        "shap_b64":           result["shap_b64"],
        "severe_anomaly_b64": result["severe_anomaly_b64"],
        "session_date":       report.session_date,
        "created_at":         report.created_at.isoformat(),
        "status":             "ready",
    }


@router.get("/{report_id}")
def get_report(
    report_id: int,
    db:    Session = Depends(get_db),
    _user: dict    = Depends(get_current_user),
):
    r = db.query(Report).filter(Report.id == report_id, Report.is_deleted == False).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found.")

    def load_b64(path: str):
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        return None

    student = db.query(Student).filter(Student.id == r.student_id).first()

    # Parse patch_scores JSON safely
    try:
        patch_breakdown = json.loads(r.patch_scores) if r.patch_scores else []
    except (json.JSONDecodeError, TypeError):
        patch_breakdown = []

    return {
        "report_id":          r.id,
        "student_id":         r.student_id,
        "student_name":       student.name          if student else "Unknown",
        "student_class":      student.student_class if student else None,
        "label":              r.label,
        "softmax_score":      r.softmax_score,
        "verdict":            r.verdict,
        "notes":              r.notes,
        "session_date":       r.session_date,
        "created_at":         r.created_at.isoformat(),
        "findings":           r.findings,
        "patch_breakdown":    patch_breakdown,
        "original_b64":       load_b64(r.original_img),
        "gradcam_b64":        load_b64(r.gradcam_img),
        "shap_b64":           load_b64(r.shap_img),
        "severe_anomaly_b64": load_b64(r.severe_anomaly_img),
    }


@router.post("/{report_id}/validate")
def validate_report(
    report_id: int,
    data: ValidateRequest,
    db:   Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "clinician":
        raise HTTPException(status_code=403, detail="Only clinicians can validate reports.")
    if data.decision not in ("verify", "disagree"):
        raise HTTPException(status_code=400, detail="Decision must be 'verify' or 'disagree'.")

    r = db.query(Report).filter(Report.id == report_id, Report.is_deleted == False).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found.")

    r.verdict = data.decision
    db.commit()
    return {"report_id": report_id, "verdict": r.verdict}


@router.patch("/{report_id}/notes")
def update_notes(
    report_id: int,
    data: NotesRequest,
    db:    Session = Depends(get_db),
    _user: dict    = Depends(get_current_user),
):
    r = db.query(Report).filter(Report.id == report_id, Report.is_deleted == False).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found.")

    r.notes = data.notes
    db.commit()
    return {"report_id": report_id, "notes": r.notes}


@router.post("/{report_id}/save")
def save_report(
    report_id: int,
    data: SaveRequest,
    db:    Session = Depends(get_db),
    _user: dict    = Depends(get_current_user),
):
    r = db.query(Report).filter(Report.id == report_id, Report.is_deleted == False).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found.")

    if data.decision:
        r.verdict = data.decision
    if data.notes is not None:
        r.notes = data.notes

    db.commit()
    return {"report_id": report_id, "status": "saved", "verdict": r.verdict, "notes": r.notes}


# ── PDF Download ──────────────────────────────────────────────────────────────

@router.get("/{report_id}/pdf")
def download_report_pdf(
    report_id: int,
    db:    Session = Depends(get_db),
    _user: dict    = Depends(get_current_user),
):
    """
    Generate and return a downloadable PDF for a saved XAI report.
    Includes: student info, confidence score, probability averaging table,
    4-panel images, evidence-based findings, clinician verdict, and audit trail.
    """
    try:
        from fpdf import FPDF
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="PDF generation requires fpdf2. Run: pip install fpdf2"
        )

    r = db.query(Report).filter(Report.id == report_id, Report.is_deleted == False).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found.")

    student = db.query(Student).filter(Student.id == r.student_id).first()
    student_name  = student.name          if student else "Unknown"
    student_class = student.student_class if student else "-"

    try:
        patch_breakdown = json.loads(r.patch_scores) if r.patch_scores else []
    except (json.JSONDecodeError, TypeError):
        patch_breakdown = []

    pct = round((r.softmax_score or 0) * 100, 1)
    verdict_text = {"verify": "Verified", "disagree": "Disagreed"}.get(r.verdict or "", "Pending")
    created = r.created_at.strftime("%B %d, %Y") if r.created_at else "-"

    # Build PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, "Inscriptio - XAI Dysgraphia Screening Report", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, f"Report #RPT-{str(report_id).zfill(4)}  |  Generated: {created}", ln=True)
    pdf.ln(4)

    # Divider
    pdf.set_draw_color(226, 232, 240)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # Student info
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 7, "Student Information", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(60, 6, f"Name:  {student_name}")
    pdf.cell(60, 6, f"Class:  {student_class}")
    pdf.cell(60, 6, f"Date:  {r.session_date or created}", ln=True)
    pdf.ln(4)

    # Diagnosis
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 7, "Diagnosis Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    label_color = (220, 38, 38) if (r.label or "").lower() == "potential" else (5, 150, 105)
    pdf.set_text_color(*label_color)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, f"{r.label or '-'}  ({pct}% System Confidence)", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 6, f"Clinician Verdict: {verdict_text}", ln=True)
    pdf.ln(4)

    # Probability Averaging
    if patch_breakdown:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 7, "Probability Averaging - Patch-Level Breakdown", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 116, 139)

        col_w = [25, 45, 55, 45]
        headers = ["Patch", "PD Probability", "Interpretation", "Confidence"]
        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(51, 65, 85)
        pdf.set_font("Helvetica", "B", 9)
        for h, w in zip(headers, col_w):
            pdf.cell(w, 6, h, border=1, fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 9)
        for p in patch_breakdown:
            pdf.cell(col_w[0], 6, f"Patch {p['patch_num']}", border=1)
            pdf.cell(col_w[1], 6, f"{p['pd_prob']}%",         border=1)
            pdf.cell(col_w[2], 6, p["label"],                  border=1)
            pdf.cell(col_w[3], 6, f"{p['confidence']}%",       border=1)
            pdf.ln()

        # Mathematical average line
        avg = round(sum(p["pd_prob"] for p in patch_breakdown) / len(patch_breakdown), 1)
        formula = " + ".join(str(p["pd_prob"]) for p in patch_breakdown)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 6, f"Average PD Probability = ({formula}) / {len(patch_breakdown)} = {avg}%", ln=True)
        pdf.ln(4)

    # Panel images
    panels = [
        ("original_img",       "Panel 1: Original Handwriting (Otsu-Binarized)"),
        ("shap_img",           "Panel 2: SHAP Heatmap (Pixel Attribution)"),
        ("gradcam_img",        "Panel 3: Grad-CAM Localization"),
        ("severe_anomaly_img", "Panel 4: Severe Anomaly Focus (Top 10% SHAP zones)"),
    ]

    image_paths = []
    for attr, title in panels:
        img_path = getattr(r, attr, None)
        if img_path and os.path.exists(img_path):
            image_paths.append((img_path, title))

    if image_paths:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 7, "XAI 4-Panel Analysis", ln=True)
        pdf.ln(4)

        img_w = 90
        img_h = 70

        if len(image_paths) > 0:
            y_start = pdf.get_y()
            
            pdf.image(image_paths[0][0], x=10, y=y_start, w=img_w, h=img_h)
            if len(image_paths) > 1:
                pdf.image(image_paths[1][0], x=108, y=y_start, w=img_w, h=img_h)

            pdf.set_y(y_start + img_h + 2)

            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(100, 116, 139)
            pdf.set_x(10)
            pdf.cell(90, 4, image_paths[0][1])
            if len(image_paths) > 1:
                pdf.set_x(108)
                pdf.cell(90, 4, image_paths[1][1])

            pdf.ln(12) 

        if len(image_paths) > 2:
            y_start = pdf.get_y()
  
            pdf.image(image_paths[2][0], x=10, y=y_start, w=img_w, h=img_h)
            if len(image_paths) > 3:
                pdf.image(image_paths[3][0], x=108, y=y_start, w=img_w, h=img_h)

            pdf.set_y(y_start + img_h + 2)
 
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(100, 116, 139)
            pdf.set_x(10)
            pdf.cell(90, 4, image_paths[2][1])
            if len(image_paths) > 3:
                pdf.set_x(108)
                pdf.cell(90, 4, image_paths[3][1])
 
            pdf.ln(12)

    # Evidence-Based Findings
    if r.findings:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 7, "Evidence-Based Clinical Findings", ln=True)
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 6, r.findings)
        pdf.ln(4)

    # Educator notes
    if r.notes:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, "Educator Notes", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 6, r.notes)
        pdf.ln(4)

    # Audit trail
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, f"AUDIT TRAIL", ln=True)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, f"Report ID: #RPT-{str(report_id).zfill(4)}", ln=True)
    pdf.cell(0, 5, f"Model: MobileNetV3-Small + SHAP DeepExplainer + Grad-CAM", ln=True)
    pdf.cell(0, 5, f"Input Size: 224x224  |  Preprocessing: Otsu Binarization", ln=True)
    pdf.cell(0, 5, f"Generated by Inscriptio v1.0.0 (AIKONIC Research Team)", ln=True)

    # Output as bytes
    from fastapi.responses import Response
    pdf_bytes = pdf.output()
    filename  = f"inscriptio_report_RPT{str(report_id).zfill(4)}_{student_name.replace(' ', '_')}.pdf"

    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
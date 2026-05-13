from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Any
import os
import base64
import json
from datetime import datetime

from database import get_db
from models import Report, Student
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["Progress & Comparison"])


def _report_calendar_day(r: Report):
    """Best-effort calendar date for spacing between assessments."""
    if r.session_date:
        try:
            return datetime.strptime(str(r.session_date).strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    try:
        return r.created_at.date() if r.created_at else None
    except Exception:
        return None


def _patch_flagged_counts(report: Report) -> tuple[int, int]:
    """(total_patches, count with PD signal >= 50% or dysgraphic label)."""
    try:
        patches: list[Any] = json.loads(report.patch_scores) if report.patch_scores else []
    except (json.JSONDecodeError, TypeError):
        patches = []
    total = len(patches)
    flagged = 0
    for p in patches:
        if not isinstance(p, dict):
            continue
        prob = p.get("pd_prob")
        lbl = str(p.get("label") or "")
        if prob is not None:
            try:
                if float(prob) >= 50.0:
                    flagged += 1
            except (TypeError, ValueError):
                if "Dysgraphic" in lbl or "PD)" in lbl:
                    flagged += 1
        elif "Dysgraphic" in lbl:
            flagged += 1
    return total, flagged


def _build_compare_summary(baseline: Report, current: Report) -> dict:
    """
    Baseline = report1, Current = report2 (selection order, not reordered by time).
    Confidence delta is (current - baseline) softmax as percentage points.
    """
    d0 = _report_calendar_day(baseline)
    d1 = _report_calendar_day(current)
    days_between = None
    if d0 and d1:
        days_between = abs((d1 - d0).days)

    s0, s1 = baseline.softmax_score, current.softmax_score
    confidence_delta_pp = None
    if s0 is not None and s1 is not None:
        confidence_delta_pp = round((float(s1) - float(s0)) * 100.0, 1)

    total0, flagged0 = _patch_flagged_counts(baseline)
    _total1, _flagged1 = _patch_flagged_counts(current)
    patches_resolved = max(0, flagged0 - _flagged1)

    return {
        "confidence_delta_percent_points": confidence_delta_pp,
        "days_between": days_between,
        "baseline": {
            "report_id": baseline.id,
            "patch_count": total0,
            "flagged_patch_count": flagged0,
        },
        "current": {
            "report_id": current.id,
            "patch_count": _total1,
            "flagged_patch_count": _flagged1,
        },
        "patches_resolved": patches_resolved,
    }


def _load_b64(path: Optional[str]) -> Optional[str]:
    if path:
        from pathlib import Path
        full_path = Path(__file__).parent / path if not os.path.isabs(path) else Path(path)
        if full_path.exists():
            with open(full_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return None


# ── GET /api/students/{id}/reports ─────────────────────────────────────────────
@router.get("/students/{student_id}/reports")
def get_student_reports(
    student_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    reports = (
        db.query(Report)
        .filter(Report.student_id == student_id, Report.is_deleted == False)
        .order_by(Report.created_at.desc())
        .all()
    )

    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "class": student.student_class,
        },
        "reports": [
            {
                "report_id": r.id,
                "label": r.label,
                "softmax_score": r.softmax_score,
                "verdict": r.verdict,
                "notes": r.notes,
                "session_date": r.session_date,
                "created_at": r.created_at.isoformat(),
            }
            for r in reports
        ],
    }


# ── GET /api/students/{id}/compare?report1_id=&report2_id= ────────────────────
@router.get("/students/{student_id}/compare")
def compare_reports(
    student_id: int,
    report1_id: int = Query(...),
    report2_id: int = Query(...),
    include_images: bool = Query(default=False, description="If true, include base64 images"),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    if report1_id == report2_id:
        raise HTTPException(status_code=400, detail="report1_id and report2_id must be different.")

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    r1 = (
        db.query(Report)
        .filter(Report.id == report1_id, Report.student_id == student_id, Report.is_deleted == False)
        .first()
    )
    r2 = (
        db.query(Report)
        .filter(Report.id == report2_id, Report.student_id == student_id, Report.is_deleted == False)
        .first()
    )
    if not r1 or not r2:
        raise HTTPException(status_code=404, detail="One or both reports not found for this student.")

    def shape(r: Report):
        patch_total, patch_flagged = _patch_flagged_counts(r)
        out = {
            "report_id": r.id,
            "label": r.label,
            "softmax_score": r.softmax_score,
            "verdict": r.verdict,
            "notes": r.notes,
            "session_date": r.session_date,
            "created_at": r.created_at.isoformat(),
            "patch_count": patch_total,
            "flagged_patch_count": patch_flagged,
        }
        if include_images:
            out.update(
                {
                    "original_b64":       _load_b64(r.original_img),
                    "shap_b64":           _load_b64(r.shap_img),
                    "gradcam_b64":        _load_b64(r.gradcam_img),
                    "severe_anomaly_b64": _load_b64(r.severe_anomaly_img),
                }
            )
        return out

    return {
        "student": {"id": student.id, "name": student.name, "class": student.student_class},
        "report1": shape(r1),
        "report2": shape(r2),
        "summary": _build_compare_summary(r1, r2),
    }


# ── GET /api/students/{id}/trend ───────────────────────────────────────────────
@router.get("/students/{student_id}/trend")
def get_trend(
    student_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    reports = (
        db.query(Report)
        .filter(Report.student_id == student_id, Report.is_deleted == False, Report.softmax_score != None)
        .order_by(Report.created_at.asc())
        .limit(limit)
        .all()
    )

    return {
        "student": {"id": student.id, "name": student.name, "class": student.student_class},
        "points": [
            {
                "report_id": r.id,
                "session_date": r.session_date,
                "created_at": r.created_at.isoformat(),
                "softmax_score": r.softmax_score,
                "label": r.label,
                "verdict": r.verdict,
            }
            for r in reports
        ],
    }
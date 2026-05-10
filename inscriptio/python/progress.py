from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import os
import base64

from database import get_db
from models import Report, Student
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["Progress & Comparison"])


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
        out = {
            "report_id": r.id,
            "label": r.label,
            "softmax_score": r.softmax_score,
            "verdict": r.verdict,
            "notes": r.notes,
            "session_date": r.session_date,
            "created_at": r.created_at.isoformat(),
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
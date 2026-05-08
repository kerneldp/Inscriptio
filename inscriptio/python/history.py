from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import json

from database import get_db
from models import Report, Student

router = APIRouter(prefix="/api/history", tags=["History Management"])


# ── Schemas ───────────────────────────────────────────────────────────────────
class BulkDeleteRequest(BaseModel):
    record_ids: List[int]
    reason: str  # Required for audit trail (soft delete)

class BulkExportRequest(BaseModel):
    record_ids: List[int]


# GET /api/history
# Returns filtered history: by date, class, or label
@router.get("")
def get_history(
    date: Optional[str] = Query(default=None, description="Filter by date YYYY-MM-DD"),
    student_class: Optional[str] = Query(default=None, description="Filter by class"),
    label: Optional[str] = Query(default=None, description="'Potential' or 'Low Potential'"),
    db: Session = Depends(get_db)
):
    query = (
        db.query(Report, Student)
        .join(Student, Report.student_id == Student.id)
        .filter(Report.is_deleted != True)
    )

    if date:
        # Prefer filtering on session_date (PDF spec), fallback to created_at for older rows
        query = query.filter((Report.session_date == date) | (Report.created_at.like(f"{date}%")))

    if student_class:
        query = query.filter(Student.student_class == student_class)

    if label:
        query = query.filter(Report.label == label)

    results = query.order_by(Report.created_at.desc()).all()

    return {
        "records": [
            {
                "report_id": r.id,
                "student_id": r.student_id,
                "student_name": s.name,
                "student_class": s.student_class,
                "label": r.label,
                "softmax_score": r.softmax_score,
                "verdict": r.verdict,
                "created_at": r.created_at.isoformat()
            }
            for r, s in results
        ]
    }


# POST /api/history/export
# Bulk export selected records (returns data for PDF generation)
@router.post("/export")
def export_records(data: BulkExportRequest, db: Session = Depends(get_db)):
    if not data.record_ids:
        raise HTTPException(status_code=400, detail="No record IDs provided")

    reports = (
        db.query(Report, Student)
        .join(Student, Report.student_id == Student.id)
        .filter(Report.id.in_(data.record_ids), Report.is_deleted != True)
        .all()
    )

    if not reports:
        raise HTTPException(status_code=404, detail="No records found")

    export_data = [
        {
            "report_id": r.id,
            "student_name": s.name,
            "student_class": s.student_class,
            "label": r.label,
            "softmax_score": r.softmax_score,
            "verdict": r.verdict,
            "notes": r.notes,
            "original_img": r.original_img,
            "shap_img": r.shap_img,
            "gradcam_img": r.gradcam_img,
            "created_at": r.created_at.isoformat()
        }
        for r, s in reports
    ]

    # Returns the data — frontend or a specialist tool handles PDF rendering
    return {
        "message": f"{len(export_data)} record(s) ready for export",
        "records": export_data
    }


# DELETE /api/history/bulk
# Soft delete with required reason (maintains audit trail)
@router.delete("/bulk")
def bulk_delete(data: BulkDeleteRequest, db: Session = Depends(get_db)):
    if not data.record_ids:
        raise HTTPException(status_code=400, detail="No record IDs provided")

    if not data.reason or len(data.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Please provide a valid reason for deletion")

    reports = (
        db.query(Report)
        .filter(Report.id.in_(data.record_ids), Report.is_deleted != True)
        .all()
    )

    if not reports:
        raise HTTPException(status_code=404, detail="No active records found with those IDs")

    for report in reports:
        report.is_deleted = True
        report.delete_reason = data.reason.strip()

    db.commit()

    return {
        "message": f"{len(reports)} record(s) successfully deleted",
        "deleted_ids": [r.id for r in reports],
        "reason": data.reason
    }

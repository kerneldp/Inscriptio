"""
Clinician workspace API — pending validation queue (prioritized).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import Report, Student, User
from auth import get_current_user

router = APIRouter(prefix="/api/clinician", tags=["Clinician"])


def _initials(name: str) -> str:
    if not name:
        return "—"
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


def _queue_sort_key(r: Report):
    urgent = 0 if getattr(r, "urgent_review", None) else 1
    high_sev = 0 if (r.softmax_score or 0) >= 0.8 else 1
    return (urgent, high_sev, -(r.softmax_score or 0), r.created_at)


def _ai_status_line(label: Optional[str], verdict: Optional[str]) -> str:
    if verdict == "verify":
        return "Validated"
    if verdict == "disagree":
        return "Requires follow-up"
    if not label or label == "—":
        return "Pending: Unclassified"
    short = "High Potential" if label == "Potential" else "Low Potential"
    return f"Pending: {short}"


def _status_badge(verdict: Optional[str]) -> str:
    if verdict == "verify":
        return "validated"
    if verdict == "disagree":
        return "followup"
    return "pending_review"


@router.get("/queue")
def get_validation_queue(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "clinician":
        raise HTTPException(status_code=403, detail="Clinician role required.")

    rows = (
        db.query(Report, Student)
        .join(Student, Report.student_id == Student.id)
        .filter(Report.is_deleted != True, Report.verdict == None)
        .all()
    )
    items = []
    for r, s in rows:
        pct = round((r.softmax_score or 0) * 100, 1)
        items.append(
            {
                "report_id":           r.id,
                "student_id":          r.student_id,
                "student_name":        s.name,
                "student_initials":    _initials(s.name),
                "created_at":          r.created_at.isoformat() if r.created_at else None,
                "ai_label":            r.label,
                "ai_status_line":      _ai_status_line(r.label, r.verdict),
                "clinical_severity":   r.softmax_score,
                "clinical_severity_pct": f"{pct}%",
                "urgent_review":       bool(getattr(r, "urgent_review", False)),
                "status_badge":        _status_badge(r.verdict),
            }
        )

    # Priority: urgent → severity ≥80% → higher score → older first (FIFO)
    rid_order = {r.id: i for i, (r, _) in enumerate(sorted(rows, key=lambda t: _queue_sort_key(t[0])))}
    items.sort(key=lambda x: rid_order.get(x["report_id"], 0))

    return {"queue": items}


@router.get("/validated")
def get_validated_reports(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Reports that have already been adjudicated (read-only browsing in workspace)."""
    if current_user.get("role") != "clinician":
        raise HTTPException(status_code=403, detail="Clinician role required.")

    rows = (
        db.query(Report, Student)
        .join(Student, Report.student_id == Student.id)
        .filter(Report.is_deleted != True, Report.verdict != None)
        .all()
    )
    items = []
    for r, s in rows:
        pct = round((r.softmax_score or 0) * 100, 1)
        items.append(
            {
                "report_id":           r.id,
                "student_id":          r.student_id,
                "student_name":        s.name,
                "student_initials":    _initials(s.name),
                "created_at":          r.created_at.isoformat() if r.created_at else None,
                "ai_label":            r.label,
                "ai_status_line":      _ai_status_line(r.label, r.verdict),
                "clinical_severity":   r.softmax_score,
                "clinical_severity_pct": f"{pct}%",
                "urgent_review":       bool(getattr(r, "urgent_review", False)),
                "status_badge":        _status_badge(r.verdict),
                "verdict":             r.verdict,
            }
        )

    items.sort(key=lambda x: x["report_id"], reverse=True)
    return {"validated": items}


class AdjudicateRequest(BaseModel):
    verdict: str                      # verify | disagree
    clinician_notes: str
    override_category: Optional[str] = None


@router.post("/report/{report_id}/adjudicate")
def adjudicate_report(
    report_id: int,
    data: AdjudicateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "clinician":
        raise HTTPException(status_code=403, detail="Clinician role required.")
    if data.verdict not in ("verify", "disagree"):
        raise HTTPException(status_code=400, detail="verdict must be 'verify' or 'disagree'.")
    if data.verdict == "disagree":
        if not (data.override_category or "").strip():
            raise HTTPException(
                status_code=400,
                detail="override_category is required when overriding the AI.",
            )
    notes = (data.clinician_notes or "").strip()
    if len(notes) < 3:
        raise HTTPException(
            status_code=400,
            detail="Diagnostic notes must be at least 3 characters.",
        )

    r = db.query(Report).filter(Report.id == report_id, Report.is_deleted == False).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found.")
    if r.verdict is not None:
        raise HTTPException(status_code=400, detail="This report has already been adjudicated.")

    u = db.query(User).filter(User.email == current_user["email"]).first()
    clinician_db_id = u.id if u else None

    r.verdict = data.verdict
    r.validated_by = clinician_db_id
    r.clinician_notes = notes
    r.override_category = (data.override_category or "").strip() or None
    if data.verdict == "verify":
        r.override_category = None

    db.commit()
    db.refresh(r)

    return {
        "report_id": report_id,
        "verdict": r.verdict,
        "clinician_notes": r.clinician_notes,
        "override_category": r.override_category,
    }

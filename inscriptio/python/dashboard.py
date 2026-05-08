from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Student, Report
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["Dashboard"])


# ── GET /api/stats/summary ────────────────────────────────────────────────────
@router.get("/stats/summary")
def get_summary(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    total_screenings = (
        db.query(Report)
        .filter(Report.is_deleted != True)
        .count()
    )
    pending_reviews = (
        db.query(Report)
        .filter(Report.is_deleted != True, Report.verdict == None)
        .count()
    )
    flagged_cases = (
        db.query(Report)
        .filter(Report.is_deleted != True, Report.label == "Potential")
        .count()
    )
    active_students = db.query(Student).count()

    return {
        "total_screenings": total_screenings,
        "pending_reviews":  pending_reviews,
        "flagged_cases":    flagged_cases,
        "active_students":  active_students,
    }


# ── GET /api/students?search= ─────────────────────────────────────────────────
@router.get("/students")
def get_students(
    search: str = Query(default="", description="Filter by student name"),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    query = db.query(Student)
    if search:
        query = query.filter(Student.name.ilike(f"%{search}%"))

    students = query.order_by(Student.name).all()

    result = []
    for s in students:
        latest = (
            db.query(Report)
            .filter(Report.student_id == s.id, Report.is_deleted != True)
            .order_by(Report.created_at.desc())
            .first()
        )
        latest_date = None
        if latest:
            latest_date = latest.session_date or latest.created_at.isoformat()
        result.append({
            "latest_report_id": latest.id if latest else None,
            "id":           s.id,
            "name":         s.name,
            "class":        s.student_class,
            "created_at":   s.created_at.isoformat(),
            "latest_label": latest.label              if latest else None,
            "latest_score": latest.softmax_score      if latest else None,
            "latest_date":  latest_date,
        })

    return {"students": result}


# ── GET /api/activity/recent ──────────────────────────────────────────────────
@router.get("/activity/recent")
def get_recent_activity(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    reports = (
        db.query(Report, Student)
        .join(Student, Report.student_id == Student.id)
        .filter(Report.is_deleted != True)
        .order_by(Report.created_at.desc())
        .limit(4)
        .all()
    )

    return {
        "recent": [
            {
                "report_id":     r.id,
                "student_id":    r.student_id,
                "student_name":  s.name,
                "student_class": s.student_class,
                "session_date":  r.session_date,
                "label":         r.label,
                "softmax_score": r.softmax_score,
                "created_at":    r.created_at.isoformat(),
            }
            for r, s in reports
        ]
    }
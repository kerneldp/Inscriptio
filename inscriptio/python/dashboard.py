from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Student, Report
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["Dashboard"])


def _utc_week_start(now: datetime) -> datetime:
    """Monday 00:00:00 UTC for the week containing `now` (naive UTC)."""
    d = now.date()
    monday = d - timedelta(days=d.weekday())
    return datetime.combine(monday, datetime.min.time())


def _utc_day_start(now: datetime) -> datetime:
    return datetime.combine(now.date(), datetime.min.time())


# ── GET /api/stats/summary ────────────────────────────────────────────────────
@router.get("/stats/summary")
def get_summary(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    now = datetime.utcnow()
    week_start = _utc_week_start(now)
    today_start = _utc_day_start(now)

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

    screenings_this_week = (
        db.query(Report)
        .filter(Report.is_deleted != True, Report.created_at >= week_start)
        .count()
    )
    flagged_potential_today = (
        db.query(Report)
        .filter(
            Report.is_deleted != True,
            Report.label == "Potential",
            Report.created_at >= today_start,
        )
        .count()
    )
    students_new_this_week = (
        db.query(Student).filter(Student.created_at >= week_start).count()
    )

    return {
        "total_screenings": total_screenings,
        "pending_reviews":  pending_reviews,
        "flagged_cases":    flagged_cases,
        "active_students":  active_students,
        "screenings_this_week": screenings_this_week,
        "flagged_potential_today": flagged_potential_today,
        "students_new_this_week": students_new_this_week,
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
    limit: int = Query(50, ge=1, le=500, description="Max rows to return"),
    week_only: bool = Query(
        True,
        description="If true, only reports created on or after Monday 00:00 UTC this week",
    ),
):
    q = (
        db.query(Report, Student)
        .join(Student, Report.student_id == Student.id)
        .filter(Report.is_deleted != True)
    )
    if week_only:
        q = q.filter(Report.created_at >= _utc_week_start(datetime.utcnow()))
    reports = q.order_by(Report.created_at.desc()).limit(limit).all()

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
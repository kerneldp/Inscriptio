from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role          = Column(String(50), nullable=False)   # "educator" | "clinician"
    name          = Column(String(100), nullable=False)
    initials      = Column(String(10), nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)


class Student(Base):
    __tablename__ = "students"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), nullable=False)
    student_class = Column(String(50), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    reports = relationship("Report", back_populates="student")


class Report(Base):
    __tablename__ = "reports"

    id          = Column(Integer, primary_key=True, index=True)
    student_id  = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(Integer, nullable=False)

    # Image file paths (set by the ML pipeline — pages 3 & 4)
    original_img       = Column(String(500), nullable=True)
    shap_img           = Column(String(500), nullable=True)
    gradcam_img        = Column(String(500), nullable=True)
    severe_anomaly_img = Column(String(500), nullable=True)   

    # Phase 04 outputs
    patch_scores = Column(Text, nullable=True)   
    findings     = Column(Text, nullable=True)  

    # ML results
    softmax_score = Column(Float,  nullable=True)
    label         = Column(String(50), nullable=True)   # "Potential" | "Low Potential"

    # Educator context at upload (also mirrored into notes for legacy PDF/report view)
    educator_context = Column(Text, nullable=True)
    urgent_review    = Column(Boolean, default=False)

    # Clinician validation
    validated_by      = Column(Integer, nullable=True)
    verdict           = Column(String(50), nullable=True)    # "verify" | "disagree"
    notes             = Column(Text,   nullable=True)        # legacy / educator autosave (synced with educator_context)
    clinician_notes   = Column(Text, nullable=True)          # official HITL observation to educator
    override_category = Column(String(120), nullable=True)   # required when verdict == disagree

    # Session metadata (used for progress comparison)
    session_date = Column(String(20), nullable=True)  # YYYY-MM-DD

    # Soft delete
    is_deleted    = Column(Boolean, default=False)
    delete_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="reports")
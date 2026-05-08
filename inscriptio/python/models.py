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
    email         = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role          = Column(String, nullable=False)   # "educator" | "clinician"
    name          = Column(String, nullable=False)
    initials      = Column(String, nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)


class Student(Base):
    __tablename__ = "students"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String, nullable=False)
    student_class = Column(String, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    reports = relationship("Report", back_populates="student")


class Report(Base):
    __tablename__ = "reports"

    id          = Column(Integer, primary_key=True, index=True)
    student_id  = Column(Integer, ForeignKey("students.id"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"),    nullable=False)

    # Image file paths (set by the ML pipeline — pages 3 & 4)
    original_img = Column(String, nullable=True)
    shap_img     = Column(String, nullable=True)
    gradcam_img  = Column(String, nullable=True)

    # ML results
    softmax_score = Column(Float,  nullable=True)
    label         = Column(String, nullable=True)   # "Potential" | "Low Potential"

    # Clinician validation
    validated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verdict      = Column(String, nullable=True)    # "verify" | "disagree"
    notes        = Column(Text,   nullable=True)

    # Session metadata (used for progress comparison)
    session_date = Column(String, nullable=True)  # YYYY-MM-DD

    # Soft delete
    is_deleted    = Column(Boolean, default=False)
    delete_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="reports")
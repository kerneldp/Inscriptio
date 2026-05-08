"""
seed.py — Run once to populate the database with demo data.
Usage:  python seed.py
"""
from datetime import datetime, timedelta
import random

from database import engine, SessionLocal, Base
from models import Student, Report

Base.metadata.create_all(bind=engine)

STUDENTS = [
    ("Ana Reyes",      "Grade 3-A"),
    ("Ben Cruz",       "Grade 3-A"),
    ("Carla Domingo",  "Grade 3-B"),
    ("Diego Santos",   "Grade 3-B"),
    ("Elena Flores",   "Grade 4-A"),
    ("Felix Torres",   "Grade 4-A"),
    ("Gia Mendoza",    "Grade 4-B"),
    ("Hector Ramos",   "Grade 4-B"),
    ("Isla Villanueva","Grade 5-A"),
    ("Jose Castillo",  "Grade 5-A"),
]

def seed():
    db = SessionLocal()
    try:
        if db.query(Student).count() > 0:
            print("Database already seeded — skipping.")
            return

        base_date = datetime.utcnow() - timedelta(days=90)

        for i, (name, cls) in enumerate(STUDENTS):
            student = Student(name=name, student_class=cls)
            db.add(student)
            db.flush()

            # Give each student 2–4 screening reports spread over time
            num_reports = random.randint(2, 4)
            for j in range(num_reports):
                score  = round(random.uniform(0.45, 0.95), 4)
                label  = "Potential" if score >= 0.70 else "Low Potential"
                offset = timedelta(days=j * 25 + random.randint(0, 5))

                report = Report(
                    student_id    = student.id,
                    uploaded_by   = 1,           # placeholder — no users table seeded
                    softmax_score = score,
                    label         = label,
                    verdict       = random.choice(["verify", "disagree", None]),
                    notes         = "Auto-generated demo record." if j == 0 else None,
                    created_at    = base_date + offset,
                )
                db.add(report)

        db.commit()
        print(f"Seeded {len(STUDENTS)} students with reports.")
    finally:
        db.close()

# Give
if __name__ == "__main__":
    seed()

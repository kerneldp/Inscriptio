# Inscriptio Backend

## Setup & Running

### 1. Install Python
Make sure Python 3.10+ is installed. Check with:
```
python --version
```

### 2. Open terminal inside the `backend/` folder

### 3. Install dependencies
```
pip install -r requirements.txt
```

### 4. Run the server
```
python -m uvicorn main:app --reload
```

Server will start at: http://localhost:8000

### 5. View API docs (auto-generated)
Open browser and go to: http://localhost:8000/docs

---

## API Endpoints

### Auth (Part 1)
| Method | URL | Description |
|--------|-----|-------------|
| POST | /api/auth/register | Register new user |
| POST | /api/auth/login | Login, returns token |
| GET  | /api/auth/me | Get current user info |

### Dashboard (Part 2)
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/dashboard/summary | Summary cards data |
| GET | /api/students?search= | Student directory |
| GET | /api/activity/recent | Latest 4 reports |

### Progress & Comparison (Part 5)
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/students/:id/reports | All reports for a student |
| GET | /api/students/:id/compare?report1_id=&report2_id= | Side-by-side comparison |
| GET | /api/students/:id/trend | Softmax scores over time |

### History (Part 6)
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/history?date=&student_class=&label= | Filtered history |
| POST | /api/history/export | Bulk export records |
| DELETE | /api/history/bulk | Soft delete with reason |

---

## File Structure
```
backend/
├── main.py          ← Entry point, run this
├── database.py      ← SQLite connection setup
├── models.py        ← Database tables (User, Student, Report)
├── auth.py          ← Part 1: Authentication
├── dashboard.py     ← Part 2: Dashboard
├── progress.py      ← Part 5: Progress & Comparison
├── history.py       ← Part 6: History Management
├── requirements.txt ← Python packages to install
└── inscriptio.db   ← Auto-created SQLite database
```

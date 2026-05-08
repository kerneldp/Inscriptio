from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext

# ── Config ────────────────────────────────────────────────────────────────────
from settings import settings
from database import get_db
from models import User

SECRET_KEY = settings.secret_key
ALGORITHM = settings.jwt_algorithm
TOKEN_EXPIRE_HOURS = settings.token_expire_hours

router = APIRouter(prefix="/api/auth", tags=["Auth"])
bearer = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Hard-coded demo accounts ──────────────────────────────────────────────────
DEMO_USERS = [
    {
        "email":    "educator@inscriptio.edu",
        "password": "educator123",
        "role":     "educator",
        "name":     "M. Reyes",
        "initials": "MR",
    },
    {
        "email":    "clinician@inscriptio.edu",
        "password": "clinician123",
        "role":     "clinician",
        "name":     "Dr. A. Santos",
        "initials": "AS",
    },
]


# ── Schemas ───────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email:    str
    password: str
    role:     str = ""

class RegisterRequest(BaseModel):
    email: str
    password: str
    role: str  # educator | clinician
    name: str


# ── Helpers ───────────────────────────────────────────────────────────────────
def create_token(user: dict) -> str:
    payload = {
        "email":    user["email"],
        "role":     user["role"],
        "name":     user["name"],
        "initials": user["initials"],
        "exp":      datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def _hash_password(password: str) -> str:
    return pwd_context.hash(password)

def _verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer)
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization header required.")
    return decode_token(credentials.credentials)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    role = (data.role or "").strip().lower()

    # Prefer DB-backed auth if user exists
    db_user = db.query(User).filter(User.email == email).first()
    if db_user:
        if not _verify_password(data.password, db_user.password_hash):
            raise HTTPException(status_code=401, detail="Incorrect email or password.")
        if role and role != db_user.role:
            raise HTTPException(status_code=401, detail="Role does not match this account.")
        token_user = {
            "email": db_user.email,
            "role": db_user.role,
            "name": db_user.name,
            "initials": db_user.initials,
        }
        return {"token": create_token(token_user), "user": token_user}

    # Fallback to demo accounts (for local dev)
    if settings.demo_mode:
        user = next(
            (u for u in DEMO_USERS
             if u["email"] == email
             and u["password"] == data.password
             and (not role or u["role"] == role)),
            None,
        )
        if not user:
            raise HTTPException(status_code=401, detail="Incorrect email, password, or role.")
        token_user = {
            "email": user["email"],
            "role": user["role"],
            "name": user["name"],
            "initials": user["initials"],
        }
        return {"token": create_token(token_user), "user": token_user}

    raise HTTPException(status_code=401, detail="Account not found.")


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    role = data.role.strip().lower()
    if role not in ("educator", "clinician"):
        raise HTTPException(status_code=400, detail="Role must be 'educator' or 'clinician'.")
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered.")

    name = data.name.strip()
    initials = "".join([p[0].upper() for p in name.split()[:2]]) or "U"

    user = User(
        email=email,
        password_hash=_hash_password(data.password),
        role=role,
        name=name,
        initials=initials,
    )
    db.add(user)
    db.commit()

    token_user = {"email": user.email, "role": user.role, "name": user.name, "initials": user.initials}
    return {"token": create_token(token_user), "user": token_user}


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user
"""
main.py — FastAPI serving layer.

Two endpoints exist on purpose:
  - POST /predict     exactly as specified for the hybrid model:
                       { "url": "..." } -> { "url", "prediction": "Safe"|"Unsafe", "confidence" }
                       Always uses the hybrid ("Default") model.
  - POST /api/check    the general endpoint the React frontend actually calls,
                       supports model selection (default + every experiment
                       model) and returns reasons alongside the verdict.
  - GET  /health       demo/health-check endpoint.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
import os

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session

from app import statistical_models
from app import hybrid_model
from app import reputation
from app.explain import generate_reasons
from app.database import engine, get_db, Base
from app import models_db
from app import auth

MAX_URL_LENGTH = 2048


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading models...")
    statistical_models.load_all()
    hybrid_model.load_hybrid_model()
    print("Setting up database...")
    Base.metadata.create_all(bind=engine)
    print("Startup complete.")
    yield


app = FastAPI(title="SafeBrowse API", lifespan=lifespan)

# Dev-friendly CORS. Tighten this to your actual frontend origin before
# deploying (e.g. allow_origins=["https://yourdomain.com"]).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=MAX_URL_LENGTH)


class PredictResponse(BaseModel):
    url: str
    prediction: str  # "Safe" | "Unsafe"
    confidence: float


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime


class HistoryItem(BaseModel):
    id: int
    url: str
    model: str
    verdict: str
    confidence: float
    created_at: datetime


def get_current_user_optional(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
) -> Optional[models_db.User]:
    """Returns the logged-in user if a valid Bearer token was sent,
    otherwise None — guests can still use the checker without an account."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    payload = auth.decode_access_token(token)
    if not payload:
        return None
    user = db.query(models_db.User).filter(models_db.User.email == payload.get("sub")).first()
    return user


def get_current_user_required(
    user: Optional[models_db.User] = Depends(get_current_user_optional),
) -> models_db.User:
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user


class CheckRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=MAX_URL_LENGTH)
    model: str = "default"


class CheckResponse(BaseModel):
    verdict: str  # "safe" | "unsafe"
    confidence: float
    reasons: list[str]
    model: str
    note: str | None = None  # e.g. explains a temporary fallback in effect

# Used for "Default" when the hybrid model isn't loaded yet — chosen for
# best recall among the trained statistical models (see training/train_statistical.py
# metrics). This is a transparent, temporary stand-in, not a substitute for
# the real hybrid model.
FALLBACK_MODEL_KEY = "dt"


def _validate_url(url: str):
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL must not be empty.")
    if len(url) > MAX_URL_LENGTH:
        raise HTTPException(status_code=400, detail=f"URL exceeds {MAX_URL_LENGTH} characters.")
    return url


@app.get("/health")
def health():
    return {
        "status": "ok",
        "hybrid_model_loaded": hybrid_model.is_available(),
        "statistical_models_loaded": statistical_models.available_models(),
    }


@app.post("/api/signup", response_model=TokenResponse)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(models_db.User).filter(models_db.User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user = models_db.User(email=req.email, password_hash=auth.hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = auth.create_access_token({"sub": user.email})
    return TokenResponse(access_token=token, email=user.email)


@app.post("/api/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models_db.User).filter(models_db.User.email == req.email).first()
    if not user or not auth.verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = auth.create_access_token({"sub": user.email})
    return TokenResponse(access_token=token, email=user.email)


@app.get("/api/me", response_model=UserResponse)
def me(user: models_db.User = Depends(get_current_user_required)):
    return UserResponse(id=user.id, email=user.email, created_at=user.created_at)


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    """Exact contract requested for the hybrid model demo."""
    url = _validate_url(req.url)
    if not hybrid_model.is_available():
        raise HTTPException(
            status_code=503,
            detail="Hybrid model is not loaded yet. Add model files to models/hybrid/ and restart.",
        )
    verdict, confidence = hybrid_model.predict(url)
    return PredictResponse(
        url=url,
        prediction="Unsafe" if verdict == "unsafe" else "Safe",
        confidence=confidence,
    )


@app.post("/api/check", response_model=CheckResponse)
def check(
    req: CheckRequest,
    db: Session = Depends(get_db),
    user: Optional[models_db.User] = Depends(get_current_user_optional),
):
    """General endpoint used by the frontend. Supports 'default' (hybrid)
    plus every experiment-tier model key (rf, dt, lr, nb, svm, xgb, ...).
    Every check is logged to history — user_id is set if logged in,
    left null for guests, so guests can still use the tool per the
    product decision that login isn't required."""
    url = _validate_url(req.url)
    model_key = req.model
    note = None

    if reputation.is_trusted(url):
        verdict, confidence, reasons = "safe", 0.99, ["Domain matches a known, trusted entry"]
    elif model_key == "default":
        if hybrid_model.is_available():
            verdict, confidence = hybrid_model.predict(url)
        else:
            verdict, confidence = statistical_models.predict(FALLBACK_MODEL_KEY, url)
            note = (
                f"Default (hybrid) model isn't loaded yet — showing a temporary "
                f"result from the {FALLBACK_MODEL_KEY.upper()} model instead."
            )
        reasons = generate_reasons(url, verdict)
    else:
        try:
            verdict, confidence = statistical_models.predict(model_key, url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        reasons = generate_reasons(url, verdict)

    entry = models_db.CheckHistory(
        user_id=user.id if user else None,
        url=url,
        model=model_key,
        verdict=verdict,
        confidence=confidence,
    )
    db.add(entry)
    db.commit()

    return CheckResponse(verdict=verdict, confidence=confidence, reasons=reasons, model=model_key, note=note)


@app.get("/api/history", response_model=list[HistoryItem])
def history(
    db: Session = Depends(get_db),
    user: models_db.User = Depends(get_current_user_required),
    limit: int = 50,
):
    rows = (
        db.query(models_db.CheckHistory)
        .filter(models_db.CheckHistory.user_id == user.id)
        .order_by(models_db.CheckHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return rows


# ---- Minimal admin view ----
# Deliberately simple for now: a shared key via header, not full admin
# auth/roles/subdomain (that's future work per the original roadmap).
# Set ADMIN_KEY as an environment variable before deploying anywhere
# public — the default below is for local dev only.
ADMIN_KEY = os.environ.get("ADMIN_KEY", "dev-admin-key")


@app.get("/api/admin/users")
def admin_list_users(db: Session = Depends(get_db), x_admin_key: Optional[str] = Header(None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key.")

    users = db.query(models_db.User).order_by(models_db.User.created_at.desc()).all()
    result = []
    for u in users:
        check_count = db.query(models_db.CheckHistory).filter(models_db.CheckHistory.user_id == u.id).count()
        result.append({
            "id": u.id,
            "email": u.email,
            "created_at": u.created_at,
            "total_checks": check_count,
        })
    return result
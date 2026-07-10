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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import statistical_models
from app import hybrid_model
from app import reputation
from app.explain import generate_reasons

MAX_URL_LENGTH = 2048


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading models...")
    statistical_models.load_all()
    hybrid_model.load_hybrid_model()
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


class CheckRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=MAX_URL_LENGTH)
    model: str = "default"


class CheckResponse(BaseModel):
    verdict: str  # "safe" | "unsafe"
    confidence: float
    reasons: list[str]
    model: str


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
def check(req: CheckRequest):
    """General endpoint used by the frontend. Supports 'default' (hybrid)
    plus every experiment-tier model key (rf, dt, lr, nb, svm, xgb, ...)."""
    url = _validate_url(req.url)
    model_key = req.model

    if reputation.is_trusted(url):
        return CheckResponse(
            verdict="safe",
            confidence=0.99,
            reasons=["Domain matches a known, trusted entry"],
            model=model_key,
        )

    if model_key == "default":
        if not hybrid_model.is_available():
            raise HTTPException(
                status_code=503,
                detail="Default (hybrid) model is not loaded yet. "
                       "Add model files to models/hybrid/ and restart, "
                       "or pick a model under Experiment for now.",
            )
        verdict, confidence = hybrid_model.predict(url)
    else:
        try:
            verdict, confidence = statistical_models.predict(model_key, url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    reasons = generate_reasons(url, verdict)
    return CheckResponse(verdict=verdict, confidence=confidence, reasons=reasons, model=model_key)

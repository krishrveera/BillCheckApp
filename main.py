import sys
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

from models import PatientBill, VerificationReport
from data.synthetic_bills import get_synthetic_bills
from pipeline.extractor import bill_to_text
from pipeline.comparator import verify_bill
from pipeline.scorer import generate_report
from auth import router as auth_router, get_current_user, APP_SECRET_KEY


# Store synthetic data in app state
PATIENTS: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load synthetic bills on startup
    for patient_data in get_synthetic_bills():
        PATIENTS[patient_data["id"]] = patient_data
    print(f"Loaded {len(PATIENTS)} synthetic patient bills")
    yield


app = FastAPI(title="BillCheck", description="Deterministic Medical Bill Verification", lifespan=lifespan)

# Session middleware (must be added before OAuth routes)
app.add_middleware(SessionMiddleware, secret_key=APP_SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount auth routes
app.include_router(auth_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/patients")
async def list_patients(user: dict = Depends(get_current_user)):
    """List all synthetic patients with summary info."""
    summaries = []
    for pid, data in PATIENTS.items():
        bill: PatientBill = data["bill"]
        summaries.append({
            "id": pid,
            "name": bill.patient_name,
            "mrn": bill.mrn,
            "facility": bill.facility_name,
            "admission_date": bill.admission_date,
            "discharge_date": bill.discharge_date,
            "primary_diagnosis": bill.primary_diagnosis_icd10,
            "total_billed": bill.total_billed,
            "line_items_count": len(bill.line_items),
            "known_error_count": len(data["known_errors"]),
        })
    return {"patients": summaries}


@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: str, user: dict = Depends(get_current_user)):
    """Get full bill details and known errors for a patient."""
    if patient_id not in PATIENTS:
        raise HTTPException(status_code=404, detail="Patient not found")
    data = PATIENTS[patient_id]
    return {
        "id": patient_id,
        "bill": data["bill"].model_dump(),
        "known_errors": data["known_errors"],
    }


@app.get("/api/patients/{patient_id}/bill-text")
async def get_bill_text(patient_id: str, user: dict = Depends(get_current_user)):
    """Get formatted text version of the bill."""
    if patient_id not in PATIENTS:
        raise HTTPException(status_code=404, detail="Patient not found")
    text = bill_to_text(PATIENTS[patient_id]["bill"])
    return {"bill_text": text}


@app.post("/api/verify/{patient_id}")
async def verify_patient(patient_id: str, user: dict = Depends(get_current_user)):
    """Run full deterministic verification pipeline on a synthetic bill."""
    if patient_id not in PATIENTS:
        raise HTTPException(status_code=404, detail="Patient not found")

    data = PATIENTS[patient_id]
    bill: PatientBill = data["bill"]

    start = time.perf_counter()
    issues = verify_bill(bill)
    report = generate_report(bill, issues)
    elapsed_ms = (time.perf_counter() - start) * 1000

    return {
        "report": report.model_dump(),
        "known_errors": data["known_errors"],
        "latency_ms": round(elapsed_ms, 2),
    }


@app.post("/api/verify-custom")
async def verify_custom(bill: PatientBill, user: dict = Depends(get_current_user)):
    """Verify a custom bill submitted as JSON."""
    start = time.perf_counter()
    issues = verify_bill(bill)
    report = generate_report(bill, issues)
    elapsed_ms = (time.perf_counter() - start) * 1000

    return {
        "report": report.model_dump(),
        "latency_ms": round(elapsed_ms, 2),
    }


# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))

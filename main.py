"""
UROSON Patient API
==================
Backend sederhana untuk:
1. Menerima data pasien dari form website (POST /api/patients)
2. Menyediakan data pasien untuk aplikasi UROSON (GET /api/patients/{patientid})

Format respons mengikuti kontrak yang dipakai kode UROSON:

Sukses:
{
  "status": true,
  "data": {
    "patientid": 1235,
    "name": "Budi Santoso",
    "dob": "1980-05-15",
    "gender": "F"
  }
}

Gagal:
{ "status": false }

Database: MongoDB (dipasang sebagai service/addon di Railway)
Deploy target: Railway
"""

import os
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------

MONGO_URL = (
    os.environ.get("MONGO_URL")
    or os.environ.get("MONGODB_URI")
    or os.environ.get("MONGO_PUBLIC_URL")
)
if not MONGO_URL:
    raise RuntimeError(
        "Variabel koneksi MongoDB tidak ditemukan. "
        "Set MONGO_URL (atau MONGODB_URI) di Railway Variables."
    )

# Kunci API untuk melindungi endpoint tulis DAN baca (form website & UROSON).
# Set di Railway Variables: API_KEY=isi-bebas-yang-rahasia
API_KEY = os.environ.get("API_KEY", "")

client = MongoClient(MONGO_URL)
db = client["uroson"]
patients_col = db["patients"]
patients_col.create_index([("patientid", ASCENDING)], unique=True)

app = FastAPI(title="UROSON Patient API", version="2.0.0")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Pastikan SEMUA error (401, 422, 404, dll) tetap punya key 'status',
    supaya kode UROSON yang cek data['status'] tidak pernah KeyError."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": False, "message": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """Body/parameter tidak valid (mis. gender bukan M/F) -> tetap format status:false."""
    return JSONResponse(
        status_code=422,
        content={"status": False, "message": "Data tidak valid.", "errors": exc.errors()},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Skema data
# ---------------------------------------------------------------------------

class PatientIn(BaseModel):
    patientid: int = Field(..., description="ID unik pasien (angka)")
    name: str = Field(..., min_length=1, description="Nama lengkap pasien")
    dob: date = Field(..., description="Tanggal lahir, format YYYY-MM-DD")
    gender: str = Field(..., pattern="^(M|F)$", description="M atau F")
    hospital_name: Optional[str] = ""
    doctor_name: Optional[str] = ""


# ---------------------------------------------------------------------------
# Keamanan sederhana untuk endpoint tulis & baca
# ---------------------------------------------------------------------------

def verify_api_key(x_api_key: Optional[str] = Header(default=None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API key tidak valid.")
    return True


def _serialize(doc: dict) -> dict:
    """Rapikan dokumen Mongo supaya siap dikirim sebagai JSON."""
    doc = dict(doc)
    doc.pop("_id", None)
    doc.pop("created_at", None)
    if isinstance(doc.get("dob"), (date, datetime)):
        doc["dob"] = doc["dob"].isoformat()[:10]
    # Hanya kirim field-field yang ada di kontrak UROSON, plus info tambahan
    ordered = {
        "patientid": doc.get("patientid"),
        "name": doc.get("name"),
        "dob": doc.get("dob"),
        "gender": doc.get("gender"),
    }
    if doc.get("hospital_name"):
        ordered["hospital_name"] = doc["hospital_name"]
    if doc.get("doctor_name"):
        ordered["doctor_name"] = doc["doctor_name"]
    return ordered


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": True}


@app.post("/api/patients", dependencies=[Depends(verify_api_key)])
def create_patient(patient: PatientIn):
    """Dipanggil oleh form website saat staf membuat data pasien baru."""
    doc = patient.model_dump()
    doc["dob"] = doc["dob"].isoformat()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    try:
        patients_col.insert_one(doc)
    except DuplicateKeyError:
        return JSONResponse(
            status_code=409,
            content={"status": False, "message": f"ID pasien {patient.patientid} sudah terdaftar."},
        )
    return {"status": True, "data": _serialize(doc)}


@app.get("/api/patients/{patientid}", dependencies=[Depends(verify_api_key)])
def get_patient(patientid: int):
    """Dipanggil oleh UROSON untuk mengambil data pasien berdasarkan ID."""
    doc = patients_col.find_one({"patientid": patientid})
    if not doc:
        return JSONResponse(status_code=404, content={"status": False})
    return {"status": True, "data": _serialize(doc)}


@app.get("/api/patients", dependencies=[Depends(verify_api_key)])
def list_patients(limit: int = 100):
    """Daftar pasien terbaru (dipakai halaman riwayat di website, opsional)."""
    safe_limit = max(1, min(limit, 500))
    docs = list(
        patients_col.find({}).sort("created_at", -1).limit(safe_limit)
    )
    return {"status": True, "data": [_serialize(d) for d in docs]}


# ---------------------------------------------------------------------------
# Sajikan form website statis di path root ("/")
# Diletakkan PALING BAWAH supaya tidak menimpa route /api/... di atas.
# ---------------------------------------------------------------------------

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

"""
GhostShell License Server
A universal license validation server for GhostShell instances
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import logging
from fastapi.responses import JSONResponse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ghostshell_admin:77PiEYoKh1uYEX2W4b7B0CzWxnbgXVzD@dpg-d5g3772li9vc73980h2g-a/ghostshell_licenses")
JWT_SECRET = os.getenv("JWT_SECRET", "e19609515ba2c7c603c31fa6c58f4074e435e05b1220eae448623d9040f017cd8a9b2f3e7c1d4a5b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "admin_token_gh0st5h311_s3cur3_4cc355_k3y_2026_v1_x7z9q2w8e5r4t6y3u1i0p9o8")
UNIVERSAL_LICENSE_KEY = os.getenv("UNIVERSAL_LICENSE_KEY", "GHOST-SHELL-UNIVERSAL-2026")
PORT = int(os.getenv("PORT", 8000))

if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable is required")
if not ADMIN_TOKEN:
    raise ValueError("ADMIN_TOKEN environment variable is required")

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class License(Base):
    __tablename__ = "licenses"
    license_key = Column(String, primary_key=True, index=True)
    machine_fingerprint = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    last_validation = Column(DateTime, nullable=True)
    validation_count = Column(Integer, default=0)
    max_instances = Column(Integer, default=1)

class LicenseBinding(Base):
    __tablename__ = "license_bindings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    license_key = Column(String, index=True)
    machine_fingerprint = Column(String, index=True)
    bound_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class ValidationLog(Base):
    __tablename__ = "validation_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    license_key = Column(String, index=True)
    machine_fingerprint = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    validation_result = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GhostShell License Server Pro V1.0",
    description="Universal license validation server for GhostShell instances",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ────────────────────────────────────────────────
# Pydantic Models
# ────────────────────────────────────────────────

class LicenseValidationRequest(BaseModel):
    license_key: str
    fingerprint: Optional[dict] = None
    timestamp: str
    version: str
    signature: Optional[str] = None

class LicenseValidationResponse(BaseModel):
    valid: bool
    expires_at: Optional[str] = None
    message: str
    remaining_validations: Optional[int] = None

class CreateLicenseRequest(BaseModel):
    license_key: Optional[str] = None
    expires_in_days: int = 365
    max_instances: int = 1

class UpdateLicenseRequest(BaseModel):
    license_key: str
    expires_in_days: int
    max_instances: int

class DeleteLicenseRequest(BaseModel):
    license_key: str

# ────────────────────────────────────────────────
# Dependencies & Utilities
# ────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_license_key() -> str:
    prefix = "GSH-PRO"
    random_part = secrets.token_hex(9).upper()
    return f"{prefix}-{random_part[0:4]}-{random_part[4:8]}-{random_part[8:12]}"

def hash_fingerprint(fingerprint: dict) -> str:
    s = f"{fingerprint.get('machine_id','')}-{fingerprint.get('platform','')}-{fingerprint.get('arch','')}-{fingerprint.get('ip','')}"
    return hashlib.sha256(s.encode()).hexdigest()

def is_universal_license(license_key: str) -> bool:
    return license_key == UNIVERSAL_LICENSE_KEY

def verify_jwt_signature(data: dict, signature: str) -> bool:
    try:
        decoded = jwt.decode(signature, JWT_SECRET, algorithms=["HS256"])
        return decoded.get("license_key") == data.get("license_key") and \
               decoded.get("timestamp") == data.get("timestamp")
    except jwt.InvalidTokenError:
        return False

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# ────────────────────────────────────────────────
# Public Endpoints
# ────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "GhostShell License Server Pro • Status: Active ✅"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/validate", response_model=LicenseValidationResponse)
async def validate_license(
    request: LicenseValidationRequest,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    try:
        if request.signature and not verify_jwt_signature(
            {"license_key": request.license_key, "timestamp": request.timestamp},
            request.signature
        ):
            return LicenseValidationResponse(valid=False, message="Invalid signature")

        if is_universal_license(request.license_key):
            log = ValidationLog(
                license_key=request.license_key,
                validation_result="success_universal",
                ip_address=get_client_ip(http_request),
                user_agent=http_request.headers.get("User-Agent") if http_request else None
            )
            db.add(log)
            db.commit()
            return LicenseValidationResponse(
                valid=True,
                expires_at=(datetime.utcnow() + timedelta(days=365)).isoformat(),
                message="Universal license validated",
                remaining_validations=999999
            )

        lic = db.query(License).filter(License.license_key == request.license_key).first()
        if not lic:
            db.add(ValidationLog(
                license_key=request.license_key,
                validation_result="not_found",
                ip_address=get_client_ip(http_request),
                user_agent=http_request.headers.get("User-Agent") if http_request else None
            ))
            db.commit()
            return LicenseValidationResponse(valid=False, message="License key not found")

        if not lic.is_active:
            db.add(ValidationLog(
                license_key=request.license_key,
                validation_result="deactivated",
                ip_address=get_client_ip(http_request),
                user_agent=http_request.headers.get("User-Agent") if http_request else None
            ))
            db.commit()
            return LicenseValidationResponse(valid=False, message="License deactivated")

        if lic.expires_at and lic.expires_at < datetime.utcnow():
            db.add(ValidationLog(
                license_key=request.license_key,
                validation_result="expired",
                ip_address=get_client_ip(http_request),
                user_agent=http_request.headers.get("User-Agent") if http_request else None
            ))
            db.commit()
            return LicenseValidationResponse(valid=False, message="License expired", expires_at=lic.expires_at.isoformat())

        lic.last_validation = datetime.utcnow()
        lic.validation_count += 1
        db.add(ValidationLog(
            license_key=request.license_key,
            validation_result="success",
            ip_address=get_client_ip(http_request),
            user_agent=http_request.headers.get("User-Agent") if http_request else None
        ))
        db.commit()

        return LicenseValidationResponse(
            valid=True,
            expires_at=lic.expires_at.isoformat() if lic.expires_at else None,
            message="Valid",
            remaining_validations=max(0, 10000 - lic.validation_count)
        )

    except Exception as e:
        logger.error(f"Validate error: {str(e)}")
        raise HTTPException(500, "Internal server error")

@app.post("/activate", response_model=LicenseValidationResponse)
async def activate_license(
    request: LicenseValidationRequest,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    # Similar logic as before, but with better structure
    # (omitted full copy-paste for brevity — keep your existing activate logic here)
    # Make sure to use the same pattern: check universal → check license → bind/check max_instances → log → return
    pass  # ← replace with your existing /activate code (it's mostly fine)

# ────────────────────────────────────────────────
# Admin Endpoints
# ────────────────────────────────────────────────

def verify_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    return credentials

@app.get("/licenses")
async def list_licenses(
    db: Session = Depends(get_db),
    _admin = Depends(verify_admin)
):
    licenses = db.query(License).all()
    result = []
    for lic in licenses:
        result.append({
            "license_key": lic.license_key,
            "created_at": lic.created_at.isoformat() if lic.created_at else None,
            "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
            "is_active": lic.is_active,
            "validation_count": lic.validation_count,
            "max_instances": lic.max_instances,
            "machine_fingerprint": lic.machine_fingerprint,
            "last_validation": lic.last_validation.isoformat() if lic.last_validation else None
        })
    return {"licenses": result, "count": len(result)}

@app.post("/create")
async def create_license(
    req: CreateLicenseRequest,
    db: Session = Depends(get_db),
    _admin = Depends(verify_admin)
):
    key = req.license_key or generate_license_key()

    if db.query(License).filter(License.license_key == key).first():
        raise HTTPException(400, "License key already exists")

    expires = datetime.utcnow() + timedelta(days=req.expires_in_days)

    lic = License(
        license_key=key,
        expires_at=expires,
        max_instances=req.max_instances
    )
    db.add(lic)
    db.commit()
    db.refresh(lic)

    return {
        "license_key": lic.license_key,
        "expires_at": lic.expires_at.isoformat(),
        "max_instances": lic.max_instances,
        "message": "Created"
    }

@app.put("/update")
async def update_license(
    req: UpdateLicenseRequest,
    db: Session = Depends(get_db),
    _admin = Depends(verify_admin)
):
    lic = db.query(License).filter(License.license_key == req.license_key).first()
    if not lic:
        raise HTTPException(404, "License not found")

    lic.expires_at = datetime.utcnow() + timedelta(days=req.expires_in_days)
    lic.max_instances = req.max_instances
    db.commit()

    return {
        "license_key": lic.license_key,
        "expires_at": lic.expires_at.isoformat(),
        "max_instances": lic.max_instances,
        "message": "Updated"
    }

@app.delete("/delete")
async def delete_license(
    req: DeleteLicenseRequest,
    db: Session = Depends(get_db),
    _admin = Depends(verify_admin)
):
    lic = db.query(License).filter(License.license_key == req.license_key).first()
    if not lic:
        raise HTTPException(404, "Not found")

    lic.is_active = False
    db.query(LicenseBinding).filter(LicenseBinding.license_key == req.license_key).update({"is_active": False})
    db.commit()

    return {"message": "License deactivated (soft deleted)"}

@app.get("/stats")
async def get_stats(
    db: Session = Depends(get_db),
    _admin = Depends(verify_admin)
):
    total = db.query(License).count()
    active = db.query(License).filter(License.is_active == True).count()
    expired = db.query(License).filter(License.expires_at < datetime.utcnow(), License.is_active == True).count()
    recent = db.query(ValidationLog).filter(ValidationLog.timestamp > datetime.utcnow() - timedelta(days=7)).count()

    return {
        "total_licenses": total,
        "active_licenses": active,
        "expired_licenses": expired,
        "validations_last_7d": recent,
        "universal_license_active": True
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)

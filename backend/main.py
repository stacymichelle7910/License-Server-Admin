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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ghostshell_admin:77PiEYoKh1uYEX2W4b7B0CzWxnbgXVzD@dpg-d5g3772li9vc73980h2g-a/ghostshell_licenses")
JWT_SECRET = os.getenv("JWT_SECRET", "e19609515ba2c7c603c31fa6c58f4074e435e05b1220eae448623d9040f017cd8a9b2f3e7c1d4a5b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "admin_token_gh0st5h311_s3cur3_4cc355_k3y_2026_v1_x7z9q2w8e5r4t6y3u1i0p9o8")
UNIVERSAL_LICENSE_KEY = os.getenv("UNIVERSAL_LICENSE_KEY", "GHOST-SHELL-UNIVERSAL-2026")
PORT = int(os.getenv("PORT", 8000))

# Fail fast on missing critical configs
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

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(
    title="GhostShell License Server Pro V1.0",
    description="Universal license validation server for GhostShell instances",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic models
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

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utility functions
def generate_license_key() -> str:
    """Generate a new license key"""
    prefix = "GHOST-SHELL-PRO"
    random_part = secrets.token_hex(8).upper()
    return f"{prefix}-{random_part[:4]}-{random_part[4:8]}-{random_part[8:12]}"

def hash_fingerprint(fingerprint: dict) -> str:
    """Create a hash of the machine fingerprint"""
    fingerprint_str = f"{fingerprint.get('machine_id', '')}-{fingerprint.get('platform', '')}-{fingerprint.get('arch', '')}-{fingerprint.get('ip', '')}"
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()

def is_universal_license(license_key: str) -> bool:
    """Check if the license key is the universal license"""
    return license_key == UNIVERSAL_LICENSE_KEY

def verify_jwt_signature(request_data: dict, signature: str) -> bool:
    """Verify JWT signature for license validation - signature verification is optional"""
    try:
        decoded = jwt.decode(signature, JWT_SECRET, algorithms=["HS256"])
        return (decoded.get("license_key") == request_data.get("license_key") and
                decoded.get("timestamp") == request_data.get("timestamp"))
    except jwt.InvalidTokenError:
        return False

def get_client_ip(request) -> str:
    """Extract client IP from request headers"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# API Routes
@app.get("/")
async def root():
    return {
        "message": "GhostShell License Server Pro",
        "version": "2.0.0",
        "status": "Your license server is active ✅"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/validate", response_model=LicenseValidationResponse)
async def validate_license(
    request: LicenseValidationRequest,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """Validate a license key without requiring fingerprint"""
    try:
        logger.info(f"License validation request for: {request.license_key}")
        
        # Verify JWT signature if provided
        if request.signature:
            request_dict = {
                "license_key": request.license_key,
                "timestamp": request.timestamp,
                "version": request.version
            }
            if not verify_jwt_signature(request_dict, request.signature):
                logger.warning(f"Invalid JWT signature for license: {request.license_key}")
                return LicenseValidationResponse(
                    valid=False,
                    message="Invalid signature"
                )
        
        # Check for universal license
        if is_universal_license(request.license_key):
            logger.info(f"Universal license validated successfully")
            
            # Log the validation
            log_entry = ValidationLog(
                license_key=request.license_key,
                machine_fingerprint=None,
                validation_result="success_universal",
                ip_address=get_client_ip(http_request) if http_request else None,
                user_agent=http_request.headers.get("User-Agent") if http_request else None
            )
            db.add(log_entry)
            db.commit()
            
            return LicenseValidationResponse(
                valid=True,
                expires_at=(datetime.utcnow() + timedelta(days=365)).isoformat(),
                message="Universal license validated successfully",
                remaining_validations=999999
            )
        
        # Check regular license in database
        license_record = db.query(License).filter(License.license_key == request.license_key).first()
        
        if not license_record:
            logger.warning(f"License not found: {request.license_key}")
            
            # Log failed validation
            log_entry = ValidationLog(
                license_key=request.license_key,
                machine_fingerprint=None,
                validation_result="not_found",
                ip_address=get_client_ip(http_request) if http_request else None,
                user_agent=http_request.headers.get("User-Agent") if http_request else None
            )
            db.add(log_entry)
            db.commit()
            
            return LicenseValidationResponse(
                valid=False,
                message="License key not found"
            )
        
        # Check if license is active
        if not license_record.is_active:
            logger.warning(f"License deactivated: {request.license_key}")
            
            log_entry = ValidationLog(
                license_key=request.license_key,
                machine_fingerprint=None,
                validation_result="deactivated",
                ip_address=get_client_ip(http_request) if http_request else None,
                user_agent=http_request.headers.get("User-Agent") if http_request else None
            )
            db.add(log_entry)
            db.commit()
            
            return LicenseValidationResponse(
                valid=False,
                message="License has been deactivated"
            )
        
        # Check expiration
        if license_record.expires_at and license_record.expires_at < datetime.utcnow():
            logger.warning(f"License expired: {request.license_key}")
            
            log_entry = ValidationLog(
                license_key=request.license_key,
                machine_fingerprint=None,
                validation_result="expired",
                ip_address=get_client_ip(http_request) if http_request else None,
                user_agent=http_request.headers.get("User-Agent") if http_request else None
            )
            db.add(log_entry)
            db.commit()
            
            return LicenseValidationResponse(
                valid=False,
                message="License has expired",
                expires_at=license_record.expires_at.isoformat()
            )
        
        # Update validation info
        license_record.last_validation = datetime.utcnow()
        license_record.validation_count += 1
        
        # Log successful validation
        log_entry = ValidationLog(
            license_key=request.license_key,
            machine_fingerprint=None,
            validation_result="success",
            ip_address=get_client_ip(http_request) if http_request else None,
            user_agent=http_request.headers.get("User-Agent") if http_request else None
        )
        db.add(log_entry)
        db.commit()
        
        logger.info(f"License validated successfully: {request.license_key}")
        
        return LicenseValidationResponse(
            valid=True,
            expires_at=license_record.expires_at.isoformat() if license_record.expires_at else None,
            message="License validated successfully",
            remaining_validations=max(0, 10000 - license_record.validation_count)
        )
        
    except Exception as e:
        logger.error(f"Error validating license: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/activate", response_model=LicenseValidationResponse)
async def activate_license(
    request: LicenseValidationRequest,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """Activate a license key and bind to machine fingerprint"""
    try:
        logger.info(f"License activation request for: {request.license_key}")
        
        # Fingerprint is required for activation
        if not request.fingerprint:
            logger.warning(f"Missing fingerprint for activation: {request.license_key}")
            return LicenseValidationResponse(
                valid=False,
                message="Machine fingerprint required for activation"
            )
        
        # Verify JWT signature if provided
        if request.signature:
            request_dict = {
                "license_key": request.license_key,
                "fingerprint": request.fingerprint,
                "timestamp": request.timestamp,
                "version": request.version
            }
            if not verify_jwt_signature(request_dict, request.signature):
                logger.warning(f"Invalid JWT signature for license: {request.license_key}")
                return LicenseValidationResponse(
                    valid=False,
                    message="Invalid signature"
                )
        
        # Check for universal license
        if is_universal_license(request.license_key):
            logger.info(f"Universal license activated successfully")
            
            # Log the activation
            log_entry = ValidationLog(
                license_key=request.license_key,
                machine_fingerprint=hash_fingerprint(request.fingerprint),
                validation_result="success_universal",
                ip_address=get_client_ip(http_request) if http_request else None,
                user_agent=http_request.headers.get("User-Agent") if http_request else None
            )
            db.add(log_entry)
            db.commit()
            
            return LicenseValidationResponse(
                valid=True,
                expires_at=(datetime.utcnow() + timedelta(days=365)).isoformat(),
                message="Universal license activated successfully",
                remaining_validations=999999
            )
        
        # Check regular license in database
        license_record = db.query(License).filter(License.license_key == request.license_key).first()
        
        if not license_record:
            logger.warning(f"License not found: {request.license_key}")
            
            # Log failed activation
            log_entry = ValidationLog(
                license_key=request.license_key,
                machine_fingerprint=hash_fingerprint(request.fingerprint),
                validation_result="not_found",
                ip_address=get_client_ip(http_request) if http_request else None,
                user_agent=http_request.headers.get("User-Agent") if http_request else None
            )
            db.add(log_entry)
            db.commit()
            
            return LicenseValidationResponse(
                valid=False,
                message="License key not found"
            )
        
        # Check if license is active
        if not license_record.is_active:
            logger.warning(f"License deactivated: {request.license_key}")
            
            log_entry = ValidationLog(
                license_key=request.license_key,
                machine_fingerprint=hash_fingerprint(request.fingerprint),
                validation_result="deactivated",
                ip_address=get_client_ip(http_request) if http_request else None,
                user_agent=http_request.headers.get("User-Agent") if http_request else None
            )
            db.add(log_entry)
            db.commit()
            
            return LicenseValidationResponse(
                valid=False,
                message="License has been deactivated"
            )
        
        # Check expiration
        if license_record.expires_at and license_record.expires_at < datetime.utcnow():
            logger.warning(f"License expired: {request.license_key}")
            
            log_entry = ValidationLog(
                license_key=request.license_key,
                machine_fingerprint=hash_fingerprint(request.fingerprint),
                validation_result="expired",
                ip_address=get_client_ip(http_request) if http_request else None,
                user_agent=http_request.headers.get("User-Agent") if http_request else None
            )
            db.add(log_entry)
            db.commit()
            
            return LicenseValidationResponse(
                valid=False,
                message="License has expired",
                expires_at=license_record.expires_at.isoformat()
            )
        
        # Update license record
        current_fingerprint = hash_fingerprint(request.fingerprint)
        
        # For first use, bind to machine
        if not license_record.machine_fingerprint:
            license_record.machine_fingerprint = current_fingerprint
            logger.info(f"License bound to machine fingerprint: {request.license_key}")
        
        # Check machine fingerprint bindings for max_instances enforcement
        current_bindings = db.query(LicenseBinding).filter(
            LicenseBinding.license_key == request.license_key,
            LicenseBinding.is_active == True
        ).all()
        
        existing_binding = next((b for b in current_bindings if b.machine_fingerprint == current_fingerprint), None)
        
        if not existing_binding:
            # Check if we can add a new binding
            if len(current_bindings) >= license_record.max_instances:
                logger.warning(f"Max instances exceeded for license: {request.license_key}")
                
                log_entry = ValidationLog(
                    license_key=request.license_key,
                    machine_fingerprint=current_fingerprint,
                    validation_result="max_instances_exceeded",
                    ip_address=get_client_ip(http_request) if http_request else None,
                    user_agent=http_request.headers.get("User-Agent") if http_request else None
                )
                db.add(log_entry)
                db.commit()
                
                return LicenseValidationResponse(
                    valid=False,
                    message=f"License already bound to {license_record.max_instances} machine(s)"
                )
            
            # Create new binding
            new_binding = LicenseBinding(
                license_key=request.license_key,
                machine_fingerprint=current_fingerprint
            )
            db.add(new_binding)
            logger.info(f"New machine binding created for license: {request.license_key}")
        else:
            # Update existing binding
            existing_binding.last_used = datetime.utcnow()
            logger.info(f"Updated existing machine binding for license: {request.license_key}")
        
        # Update validation info
        license_record.last_validation = datetime.utcnow()
        license_record.validation_count += 1
        
        # Log successful activation
        log_entry = ValidationLog(
            license_key=request.license_key,
            machine_fingerprint=current_fingerprint,
            validation_result="success",
            ip_address=get_client_ip(http_request) if http_request else None,
            user_agent=http_request.headers.get("User-Agent") if http_request else None
        )
        db.add(log_entry)
        db.commit()
        
        logger.info(f"License activated successfully: {request.license_key}")
        
        return LicenseValidationResponse(
            valid=True,
            expires_at=license_record.expires_at.isoformat() if license_record.expires_at else None,
            message="License activated successfully",
            remaining_validations=max(0, 10000 - license_record.validation_count)
        )
        
    except Exception as e:
        logger.error(f"Error activating license: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/create")
async def create_license(
    request: CreateLicenseRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new license (admin only)"""
    
    # Admin token check
    if credentials.credentials != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        license_key = request.license_key or generate_license_key()
        
        # Check if license already exists
        existing = db.query(License).filter(License.license_key == license_key).first()
        if existing:
            raise HTTPException(status_code=400, detail="License key already exists")
        
        # Create new license
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
        
        new_license = License(
            license_key=license_key,
            expires_at=expires_at,
            max_instances=request.max_instances
        )
        
        db.add(new_license)
        db.commit()
        
        logger.info(f"New license created: {license_key}")
        
        return {
            "license_key": license_key,
            "expires_at": expires_at.isoformat(),
            "max_instances": request.max_instances,
            "message": "License created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating license: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/update")
async def update_license(
    request: UpdateLicenseRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update an existing license (admin only)"""
    
    # Admin token check
    if credentials.credentials != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        license_record = db.query(License).filter(License.license_key == request.license_key).first()
        
        if not license_record:
            raise HTTPException(status_code=404, detail="License key not found")
        
        # Update license
        license_record.expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
        license_record.max_instances = request.max_instances
        db.commit()
        
        logger.info(f"License updated: {request.license_key}")
        
        return {
            "license_key": request.license_key,
            "expires_at": license_record.expires_at.isoformat(),
            "max_instances": request.max_instances,
            "message": "License updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating license: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/delete")
async def delete_license(
    request: DeleteLicenseRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a license (admin only)"""
    
    # Admin token check
    if credentials.credentials != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        license_record = db.query(License).filter(License.license_key == request.license_key).first()
        
        if not license_record:
            raise HTTPException(status_code=404, detail="License key not found")
        
        # Mark license as inactive (soft delete)
        license_record.is_active = False
        db.query(LicenseBinding).filter(LicenseBinding.license_key == request.license_key).update({"is_active": False})
        db.commit()
        
        logger.info(f"License deleted: {request.license_key}")
        
        return {
            "message": "License deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting license: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/stats")
async def get_stats(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get license statistics (admin only)"""
    
    if credentials.credentials != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        total_licenses = db.query(License).count()
        active_licenses = db.query(License).filter(License.is_active == True).count()
        expired_licenses = db.query(License).filter(
            License.expires_at < datetime.utcnow()
        ).count()
        
        recent_validations = db.query(ValidationLog).filter(
            ValidationLog.timestamp > datetime.utcnow() - timedelta(days=7)
        ).count()
        
        return {
            "total_licenses": total_licenses,
            "active_licenses": active_licenses,
            "expired_licenses": expired_licenses,
            "recent_validations": recent_validations,
            "universal_license_active": True
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)

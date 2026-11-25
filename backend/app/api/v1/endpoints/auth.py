"""Authentication, RBAC User Profile, and Security Audit Log Endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, record_audit_log, require_roles
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.db.session import get_db
from app.models.user import AuditLog, User
from app.schemas.common import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication & Security"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate user credentials and issue signed JWT access and refresh tokens."""
    user = db.execute(
        select(User).where(User.email == payload.email.lower().strip())
    ).scalar_one_or_none()

    client_ip = request.client.host if request.client else "unknown"
    if not user or not verify_password(payload.password, user.hashed_password):
        record_audit_log(
            db=db,
            action="LOGIN_FAILED",
            resource_type="USER",
            ip_address=client_ip,
            details={"email": payload.email},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        extra_claims={"email": user.email, "name": user.full_name},
    )
    refresh_token = create_refresh_token(subject=user.id, role=user.role)

    record_audit_log(
        db=db,
        action="LOGIN_SUCCESS",
        resource_type="USER",
        resource_id=user.id,
        user_id=user.id,
        ip_address=client_ip,
        details={"role": user.role},
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    )


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Return current authenticated user profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "last_login_at": current_user.last_login_at,
    }


@router.get("/audit-logs")
def list_audit_logs(
    limit: int = 50,
    current_user: User = Depends(require_roles(["EXECUTIVE_ADMIN"])),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return latest security and governance audit logs (Executive Admin only)."""
    rows = (
        db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 200)))
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "ip_address": r.ip_address,
            "details": r.details,
            "created_at": r.created_at,
        }
        for r in rows
    ]

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ActivationToken, PasswordResetToken, RefreshToken
from app.schemas import UserCreate, UserLogin, Token, PasswordResetRequest, PasswordResetConfirm, UserUpdateGroup
from app.auth import create_access_token, create_refresh_token, get_current_user
from app.email_utils import send_activation_email, send_password_reset_email
from app.security import get_password_hash, verify_password
import uuid
from datetime import datetime, timedelta


router = APIRouter()


@router.post("/register/")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password, is_active=False, group_id=1)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    activation_token = ActivationToken(
        user_id=new_user.id,
        token=str(uuid.uuid4()),
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(activation_token)
    db.commit()

    send_activation_email(user.email, activation_token.token)
    return {"message": "User registered. Check your email for activation link."}


@router.get("/activate/{token}")
def activate_account(token: str, db: Session = Depends(get_db)):
    activation_token = db.query(ActivationToken).filter(
        ActivationToken.token == token,
        ActivationToken.expires_at > datetime.utcnow()
    ).first()

    if not activation_token:
        raise HTTPException(status_code=400, detail="Invalid or expired activation token")

    user = db.query(User).filter(User.id == activation_token.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    db.delete(activation_token)
    db.commit()
    return {"message": "Account activated successfully"}

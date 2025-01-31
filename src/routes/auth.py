from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ActivationToken, PasswordResetToken, RefreshToken, UserGroup
from app.schemas import UserCreate, UserLogin, Token, PasswordResetRequest, PasswordResetConfirm, UserUpdateGroup, \
    PasswordChange
from app.auth import create_access_token, create_refresh_token, get_current_user
from app.email_utils import send_activation_email, send_password_reset_email
from app.security import get_password_hash, verify_password
import uuid
from datetime import datetime, timedelta
from app.auth import get_current_user_admin
import uuid
import re


router = APIRouter()

def validate_password(password: str):
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")
    if not re.search(r"[0-9]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character")


@router.post("/register/")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    validate_password(user.password)
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


@router.post("/change-password/")
def change_password(password_data: PasswordChange, current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user.id).first()
    if not verify_password(password_data.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")

    validate_password(password_data.new_password)
    user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


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


@router.post("/resend-activation/")
def resend_activation(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    activation_token = ActivationToken(
        user_id=user.id,
        token=str(uuid.uuid4()),
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(activation_token)
    db.commit()
    send_activation_email(user.email, activation_token.token)
    return {"message": "New activation email sent."}


@router.post("/login/")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": db_user.email, "role": db_user.group_id})
    refresh_token = create_refresh_token(data={"sub": db_user.email})

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/logout/")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).delete()
    db.commit()
    return {"message": "Logged out successfully"}


@router.post("/admin/change-group/")
def change_user_group(update_data: UserUpdateGroup, current_admin: User = Depends(get_current_user_admin),
                      db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == update_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    group = db.query(UserGroup).filter(UserGroup.id == update_data.new_group_id).first()
    if not group:
        raise HTTPException(status_code=400, detail="Invalid group ID")

    user.group_id = update_data.new_group_id
    db.commit()
    return {"message": "User group updated successfully"}


@router.post("/admin/activate-user/")
def activate_user(user_id: int, current_admin: User = Depends(get_current_user_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    db.commit()
    return {"message": "User activated successfully"}

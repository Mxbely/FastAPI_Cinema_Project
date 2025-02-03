from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import LimitOffsetPage
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session

from config import get_jwt_auth_manager
from database import Payment, PaymentStatusEnum, User, UserGroupEnum, get_db
from exceptions import BaseSecurityError
from schemas import PaymentHistoryResponse
from schemas.accounts import MessageResponseSchema
from security.http import get_token

router = APIRouter()


@router.get("/", response_model=LimitOffsetPage[PaymentHistoryResponse])
def read_payments(
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    payment_status: Optional[PaymentStatusEnum] = None,
    db: Session = Depends(get_db),
    token: str = Depends(get_token),
    jwt_manager=Depends(get_jwt_auth_manager)
):
    try:
        payload = jwt_manager.decode_access_token(token)
        token_user_id = payload.get("user_id")
    except BaseSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

    user = db.query(User).filter_by(id=token_user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.group.name != UserGroupEnum.ADMIN.value:
        return paginate(db.query(Payment).filter_by(user_id=token_user_id))

    query = db.query(Payment)

    if user_id:
        query = query.filter_by(user_id=user_id)
    if start_date:
        query = query.filter(Payment.created_at >= start_date)
    if end_date:
        query = query.filter(Payment.created_at <= end_date)
    if payment_status:
        query = query.filter_by(status=payment_status)

    payments = query.all()

    if not payments:
        return MessageResponseSchema(
            message="No payments found."
        )

    return paginate(query)


@router.get("/success")
def payment_success():
    pass


@router.get("/cancel")
def payment_cancel():
    pass

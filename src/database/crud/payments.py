from typing import Type

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import Order, Payment, PaymentItem, PaymentStatusEnum
from schemas import PaymentCreateSchema


def create_payment(payment: PaymentCreateSchema, db: Session) -> Payment:
    try:
        payment = Payment(
            user_id=payment.user_id,
            order_id=payment.order_id,
            amount=payment.amount,
            external_payment_id=payment.external_payment_id,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


def create_payment_items(
    payment: Payment, order: Order, db: Session
) -> list[PaymentItem]:
    payment_items = []
    try:
        for order_item in order.order_items:
            payment_item = PaymentItem(
                payment_id=payment.id,
                order_item_id=order_item.id,
                price_at_payment=order_item.price_at_order,
            )
            payment_items.append(payment_item)

        db.add_all(payment_items)
        db.commit()
        return payment_items
    except Exception as e:
        db.rollback()
        raise Exception(f"An error occurred while creating payment items: {e}")


def update_payment_status(
        payment: Payment | Type[Payment],
        new_status: PaymentStatusEnum,
        db: Session,
) -> Payment | Type[Payment] | None:
    if payment:
        payment.status = new_status.value
        db.commit()
        db.refresh(payment)
    return payment


def get_payment_by_session_id(
        session_id: str,
        db: Session
) -> Payment | None:
    try:
        return db.query(Payment).filter_by(external_payment_id=session_id).first()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

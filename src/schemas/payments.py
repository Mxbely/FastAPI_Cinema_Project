from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from database import PaymentStatusEnum


class PaymentSchema(BaseModel):
    user_id: int
    order_id: int
    amount: Decimal


class PaymentCreateSchema(PaymentSchema):
    external_payment_id: Optional[str]


class PaymentItemCreateSchema(BaseModel):
    payment_id: int
    order_item_id: int
    price_at_payment: Decimal


class PaymentHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    status: PaymentStatusEnum
    created_at: datetime

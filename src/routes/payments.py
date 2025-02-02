from fastapi import APIRouter

router = APIRouter()


@router.get("/success")
def payment_success():
    pass


@router.get("/cancel")
def payment_cancel():
    pass

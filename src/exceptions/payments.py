from typing import NoReturn

import stripe
from fastapi import HTTPException, status


def handle_stripe_error(e: Exception) -> NoReturn:
    """
    Handles Stripe API errors and returns appropriate HTTP responses.
    """
    errors = {
        stripe.PermissionError: status.HTTP_403_FORBIDDEN,
        stripe.APIConnectionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        stripe.APIError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        stripe.CardError: status.HTTP_400_BAD_REQUEST,
    }

    for error_type, status_code in errors.items():
        if isinstance(e, error_type):
            raise HTTPException(status_code=status_code, detail=str(e))
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
    )

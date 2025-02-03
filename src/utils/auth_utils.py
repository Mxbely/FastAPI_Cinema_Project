from typing import Type

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from database import User
from exceptions import BaseSecurityError
from security.interfaces import JWTAuthManagerInterface


def retrieve_user_id_from_token(
    token: str,
    jwt_manager: JWTAuthManagerInterface
) -> int:
    try:
        payload = jwt_manager.decode_access_token(token)
        token_user_id = int(payload.get("user_id"))
        if not token_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        return token_user_id
    except BaseSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


def retrieve_user_from_token(
    db: Session,
    token: str,
    jwt_manager: JWTAuthManagerInterface
) -> User | Type[User]:
    token_user_id = retrieve_user_id_from_token(token, jwt_manager)
    user = db.query(User).filter_by(id=token_user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

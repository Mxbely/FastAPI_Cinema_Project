from typing import Any

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=14, deprecated="auto")


def hash_password(password: str) -> Any | str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> Any | bool:
    return pwd_context.verify(plain_password, hashed_password)

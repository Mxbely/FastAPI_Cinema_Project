from idlelib.query import Query
from typing import Any

from sqlalchemy.orm import Session

from database import ActivationToken, PasswordResetToken, RefreshToken, User, UserGroup


def get_user_by_email(db: Session, email: str) -> Query | None:
    return db.query(User).filter_by(email=email).first()


def get_user_group_by_name(db: Session, name: str) -> Query | None:
    return db.query(UserGroup).filter_by(name=name).first()


def get_user_by_id(db: Session, user_id: int) -> Query | None:
    return db.query(User).filter_by(id=user_id).first()


def create_user_group_by_name(db: Session, name: str) -> UserGroup:
    user_group = UserGroup(name=name)
    db.add(user_group)
    db.commit()
    db.refresh(user_group)
    return user_group


def create_user_by_email_password_group_id(
        db: Session,
        email: str,
        password: str,
        group_id: int
) -> Any:
    new_user = User.create(
        email=str(email),
        raw_password=password,
        group_id=group_id,
    )
    db.add(new_user)
    db.flush()

    activation_token = ActivationToken(user_id=new_user.id)
    db.add(activation_token)

    db.commit()
    db.refresh(new_user)
    return new_user, activation_token


def get_activation_token_by_email_token(
        db: Session,
        email: str,
        token: Any
) -> Query | None:
    return (
        db.query(ActivationToken)
        .join(User)
        .filter(
            User.email == email,
            ActivationToken.token == token,
        )
        .first()
    )


def delete_token(db: Session, token: Any) -> None:
    db.delete(token)
    db.commit()


def delete_password_reset_token_by_user_id(db: Session, user_id: int) -> None:
    db.query(PasswordResetToken).filter_by(user_id=user_id).delete()


def create_password_reset_token_by_user_id(db: Session, user_id: int) -> Any:
    reset_token = PasswordResetToken(user_id=user_id)
    db.add(reset_token)
    db.commit()
    return reset_token


def get_password_reset_token_by_user_id(db: Session, user_id: int) -> Query | None:
    return db.query(PasswordResetToken).filter_by(user_id=user_id).first()


def db_rollback(db: Session) -> None:
    db.rollback()


def create_refresh_token_by_user_id_days_token(
        db: Session,
        user_id: int,
        days_valid: int,
        token: Any
) -> None:
    refresh_token = RefreshToken.create(
        user_id=user_id,
        days_valid=days_valid,
        token=token,
    )
    db.add(refresh_token)
    db.flush()
    db.commit()


def get_refresh_token_by_refresh_token(db: Session, refresh_token: Any) -> Query | None:
    return db.query(RefreshToken).filter_by(token=refresh_token).first()


def get_all_activation_tokens(db: Session) -> Query:
    return db.query(ActivationToken).all()


def remove_activation_token(db: Session, token: Any) -> None:
    db.delete(token)
    db.commit()

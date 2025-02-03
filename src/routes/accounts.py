from datetime import datetime, timezone
from typing import cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from config import (
    BaseAppSettings,
    get_accounts_email_notificator,
    get_jwt_auth_manager,
    get_settings,
)
from database import (
    UserGroupEnum,
    get_db,
)
from database.crud.accounts import (
    create_password_reset_token_by_user_id,
    create_refresh_token_by_user_id_days_token,
    create_user_by_email_password_group_id,
    create_user_group_by_name,
    db_rollback,
    delete_password_reset_token_by_user_id,
    delete_token,
    get_activation_token_by_email_token,
    get_password_reset_token_by_user_id,
    get_refresh_token_by_refresh_token,
    get_user_by_email,
    get_user_by_id,
    get_user_group_by_name,
)
from exceptions import BaseSecurityError
from notifications import EmailSenderInterface
from schemas.accounts import (
    MessageResponseSchema,
    PasswordResetCompleteRequestSchema,
    PasswordResetRequestSchema,
    TokenRefreshRequestSchema,
    TokenRefreshResponseSchema,
    UserActivationRequestSchema,
    UserLoginRequestSchema,
    UserLoginResponseSchema,
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
)
from security.interfaces import JWTAuthManagerInterface

router = APIRouter()


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    summary="User Registration",
    description="Register a new user with an email and password.",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {
            "description": "Conflict - User with this email already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A user with this email "
                        "test@example.com already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - "
            "An error occurred during user creation.",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred during user creation."}
                }
            },
        },
    },
)
def register_user(
    user_data: UserRegistrationRequestSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator),
) -> UserRegistrationResponseSchema:
    """
    Endpoint for user registration.

    Registers a new user, hashes their password,
    and assigns them to the default user group.
    If a user with the same email already exists, an HTTP 409 error is raised.
    In case of any unexpected issues during the creation process,
    an HTTP 500 error is returned.
    """
    existing_user = get_user_by_email(db=db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {user_data.email} already exists.",
        )

    user_group = get_user_group_by_name(db=db, name=UserGroupEnum.USER)

    if not user_group:
        user_group = create_user_group_by_name(db=db, name=UserGroupEnum.USER)

    try:
        new_user, activation_token = create_user_by_email_password_group_id(
            db=db,
            email=user_data.email,
            password=user_data.password,
            group_id=user_group.id,
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation.",
        )
    else:
        activation_link = "http://127.0.0.1/accounts/activate/"

        background_tasks.add_task(
            email_sender.send_activation_email, new_user.email, activation_link
        )

        return UserRegistrationResponseSchema.model_validate(new_user)


@router.post(
    "/activate/",
    response_model=MessageResponseSchema,
    summary="Activate User Account",
    description="Activate a user's account using their email and activation token.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - The activation token is invalid or expired, "
            "or the user account is already active.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid Token",
                            "value": {"detail": "Invalid or expired activation token."},
                        },
                        "already_active": {
                            "summary": "Account Already Active",
                            "value": {"detail": "User account is already active."},
                        },
                    }
                }
            },
        },
    },
)
def activate_account(
    activation_data: UserActivationRequestSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator),
) -> MessageResponseSchema:
    """
    Endpoint to activate a user's account.

    Verifies the activation token for a user. If valid, activates the account
    and deletes the token. If invalid or expired, raises an appropriate error.
    """
    token_record = get_activation_token_by_email_token(
        db=db, email=activation_data.email, token=activation_data.token
    )

    if not token_record or cast(datetime, token_record.expires_at).replace(
        tzinfo=timezone.utc
    ) < datetime.now(timezone.utc):
        if token_record:
            delete_token(db=db, token=token_record)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token.",
        )

    user = token_record.user
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active.",
        )

    user.is_active = True
    delete_token(db=db, token=token_record)

    login_link = "http://127.0.0.1/accounts/login/"

    background_tasks.add_task(
        email_sender.send_activation_complete_email,
        str(activation_data.email),
        login_link,
    )

    return MessageResponseSchema(message="User account activated successfully.")


@router.post(
    "/password-reset/request/",
    response_model=MessageResponseSchema,
    summary="Request Password Reset Token",
    description=(
        "Allows a user to request a password reset token. "
        "If the user exists and is active, "
        "a new token will be generated and any existing tokens will be invalidated."
    ),
    status_code=status.HTTP_200_OK,
)
def request_password_reset_token(
    data: PasswordResetRequestSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator),
) -> MessageResponseSchema:
    """
    Endpoint to request a password reset token.

    If the user exists and is active,
    invalidates any existing password reset tokens and generates a new one.
    Always responds with a success message to avoid leaking user information.
    """
    user = get_user_by_email(db=db, email=data.email)

    if not user or not user.is_active:
        return MessageResponseSchema(
            message="If you are registered, "
            "you will receive an email with instructions."
        )

    delete_password_reset_token_by_user_id(db=db, user_id=user.id)

    create_password_reset_token_by_user_id(db=db, user_id=user.id)

    password_reset_complete_link = "http://127.0.0.1/accounts/password-reset-complete/"

    background_tasks.add_task(
        email_sender.send_password_reset_email,
        str(data.email),
        password_reset_complete_link,
    )

    return MessageResponseSchema(
        message="If you are registered, you will receive an email with instructions."
    )


@router.post(
    "/reset-password/complete/",
    response_model=MessageResponseSchema,
    summary="Reset User Password",
    description="Reset a user's password if a valid token is provided.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - The provided email or token is invalid, "
            "the token has expired, or the user account is not active.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_email_or_token": {
                            "summary": "Invalid Email or Token",
                            "value": {"detail": "Invalid email or token."},
                        },
                        "expired_token": {
                            "summary": "Expired Token",
                            "value": {"detail": "Invalid email or token."},
                        },
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - "
            "An error occurred while resetting the password.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while resetting the password."
                    }
                }
            },
        },
    },
)
def reset_password(
    data: PasswordResetCompleteRequestSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator),
) -> MessageResponseSchema:
    """
    Endpoint for resetting a user's password.

    Validates the token and updates the user's password
    if the token is valid and not expired.
    Deletes the token after successful password reset.
    """
    user = get_user_by_email(db=db, email=data.email)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or token."
        )

    token_record = get_password_reset_token_by_user_id(db=db, user_id=user.id)

    expires_at = cast(datetime, token_record.expires_at).replace(tzinfo=timezone.utc)

    if (
        not token_record
        or token_record.token != data.token
        or expires_at < datetime.now(timezone.utc)
    ):
        if token_record:
            delete_token(db=db, token=token_record)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or token."
        )

    try:
        user.password = data.password
        delete_token(db=db, token=token_record)
    except SQLAlchemyError:
        db_rollback(db=db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password.",
        )

    login_link = "http://127.0.0.1/accounts/login/"

    background_tasks.add_task(
        email_sender.send_password_reset_complete_email, str(data.email), login_link
    )

    return MessageResponseSchema(message="Password reset successfully.")


@router.post(
    "/login/",
    response_model=UserLoginResponseSchema,
    summary="User Login",
    description="Authenticate a user and return access and refresh tokens.",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {
            "description": "Unauthorized - Invalid email or password.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid email or password."}
                }
            },
        },
        403: {
            "description": "Forbidden - User account is not activated.",
            "content": {
                "application/json": {
                    "example": {"detail": "User account is not activated."}
                }
            },
        },
        500: {
            "description": "Internal Server Error - "
            "An error occurred while processing the request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while processing the request."
                    }
                }
            },
        },
    },
)
def login_user(
    login_data: UserLoginRequestSchema,
    db: Session = Depends(get_db),
    settings: BaseAppSettings = Depends(get_settings),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> UserLoginResponseSchema:
    """
    Endpoint for user login.

    Authenticates a user using their email and password.
    If authentication is successful, creates a new refresh token and
    returns both access and refresh tokens.
    """
    user = get_user_by_email(db=db, email=login_data.email)
    if not user or not user.verify_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated.",
        )

    jwt_refresh_token = jwt_manager.create_refresh_token({"user_id": user.id})

    try:
        create_refresh_token_by_user_id_days_token(
            db=db,
            user_id=user.id,
            days_valid=settings.LOGIN_TIME_DAYS,
            token=jwt_refresh_token,
        )
    except SQLAlchemyError:
        db_rollback(db=db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request.",
        )

    jwt_access_token = jwt_manager.create_access_token({"user_id": user.id})
    return UserLoginResponseSchema(
        access_token=jwt_access_token,
        refresh_token=jwt_refresh_token,
    )


@router.post(
    "/refresh/",
    response_model=TokenRefreshResponseSchema,
    summary="Refresh Access Token",
    description="Refresh the access token using a valid refresh token.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - "
            "The provided refresh token is invalid or expired.",
            "content": {
                "application/json": {"example": {"detail": "Token has expired."}}
            },
        },
        401: {
            "description": "Unauthorized - Refresh token not found.",
            "content": {
                "application/json": {"example": {"detail": "Refresh token not found."}}
            },
        },
        404: {
            "description": "Not Found - "
            "The user associated with the token does not exist.",
            "content": {"application/json": {"example": {"detail": "User not found."}}},
        },
    },
)
def refresh_access_token(
    token_data: TokenRefreshRequestSchema,
    db: Session = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> TokenRefreshResponseSchema:
    """
    Endpoint to refresh an access token.

    Validates the provided refresh token, extracts the user ID from it, and issues
    a new access token. If the token is invalid or expired, an error is returned.
    """
    try:
        decoded_token = jwt_manager.decode_refresh_token(token_data.refresh_token)
        user_id = decoded_token.get("user_id")
    except BaseSecurityError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    refresh_token_record = get_refresh_token_by_refresh_token(
        db=db, refresh_token=token_data.refresh_token
    )

    if not refresh_token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found.",
        )

    user = get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    new_access_token = jwt_manager.create_access_token({"user_id": user_id})

    return TokenRefreshResponseSchema(access_token=new_access_token)

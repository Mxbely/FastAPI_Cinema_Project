import os

from fastapi import Depends

from config.settings import TestingSettings, Settings, BaseAppSettings
# from notifications import EmailSenderInterface, EmailSender
# from security.interfaces import JWTAuthManagerInterface
# from security.token_manager import JWTAuthManager
# from storages import S3StorageInterface, S3StorageClient


def get_settings() -> BaseAppSettings:
    environment = os.getenv("ENVIRONMENT", "developing")
    if environment == "testing":
        return TestingSettings()
    return Settings()


# def get_jwt_auth_manager(settings: BaseAppSettings = Depends(get_settings)) -> JWTAuthManagerInterface:
#     return JWTAuthManager(
#         secret_key_access=settings.SECRET_KEY_ACCESS,
#         secret_key_refresh=settings.SECRET_KEY_REFRESH,
#         algorithm=settings.JWT_SIGNING_ALGORITHM
#     )



# def get_s3_storage_client(settings: BaseAppSettings = Depends(get_settings)) -> S3StorageInterface:
#     return S3StorageClient(
#         endpoint_url=settings.S3_STORAGE_ENDPOINT,
#         access_key=settings.S3_STORAGE_ACCESS_KEY,
#         secret_key=settings.S3_STORAGE_SECRET_KEY,
#         bucket_name=settings.S3_BUCKET_NAME
#     )

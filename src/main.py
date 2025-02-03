from fastapi import FastAPI
from fastapi_pagination import add_pagination

from routes import accounts_router, payments_router, profiles_router

app = FastAPI(
    title="Movies Cinema",
)

api_version_prefix = "/api/v1"

app.include_router(
    accounts_router, prefix=f"{api_version_prefix}/accounts", tags=["accounts"]
)
app.include_router(
    profiles_router, prefix=f"{api_version_prefix}/profiles", tags=["profiles"]
)
app.include_router(
    payments_router, prefix=f"{api_version_prefix}/payments", tags=["payments"]
)

add_pagination(app)

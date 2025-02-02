from fastapi import FastAPI

from routes import accounts_router, profiles_router, orders_router, payments_router

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
    orders_router, prefix=f"{api_version_prefix}", tags=["orders"]
)
app.include_router(
    payments_router, prefix=f"{api_version_prefix}/payments", tags=["payments"]
)

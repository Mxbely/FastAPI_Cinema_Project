from fastapi import FastAPI

from routes import accounts_router, profiles_router
from routes.shopping_cart import router as shopping_carts_router


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


app.include_router(shopping_carts_router, prefix=f"{api_version_prefix}/carts", tags=["carts"])

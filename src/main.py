from fastapi import FastAPI
from fastapi_pagination import add_pagination
from fastapi.middleware.cors import CORSMiddleware

from routes import (
    accounts_router, movies_router, payments_router, profiles_router, orders_router
)
from routes.shopping_cart import router as shopping_carts_router

app = FastAPI(
    title="Movies Cinema",
)

api_version_prefix = "/api/v1"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    accounts_router, prefix=f"{api_version_prefix}/accounts", tags=["accounts"]
)
app.include_router(
    profiles_router, prefix=f"{api_version_prefix}/profiles", tags=["profiles"]
)
app.include_router(
    movies_router, prefix=f"{api_version_prefix}/cinema", tags=["cinema"]
)
app.include_router(
    payments_router, prefix=f"{api_version_prefix}/payments", tags=["payments"]
)
app.include_router(
    orders_router, prefix=f"{api_version_prefix}", tags=["orders"]
)

add_pagination(app)
app.include_router(
    shopping_carts_router, prefix=f"{api_version_prefix}/carts", tags=["carts"]
)

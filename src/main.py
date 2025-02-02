from fastapi import FastAPI

from routes import accounts_router, profiles_router, movies_router

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
    movies_router, prefix=f"{api_version_prefix}/cinema", tags=["cinema"]
)

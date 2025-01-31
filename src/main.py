from fastapi import FastAPI
from app.routes import auth


app = FastAPI(
    title="Movies Cinema",
)
app.include_router(auth.router)
api_version_prefix = "/api/v1"

"""FastAPI application entry."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.routers import orb, reports
from src.app.services import db
from src.settings import settings

app = FastAPI(
    title="place-tech-platform",
    description=("A real estate reporting demo: sales, rentals, offices, marketing, data checks and a data agent. "
                 "Built for a job application; not affiliated with or endorsed by Place Estate Agents. All data is synthetic."),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Write-Token", "X-Actor"],
)

for module in (reports, orb):
    app.include_router(module.router)


@app.get("/health")
def health() -> dict[str, str]:
    db.connection()
    return {"status": "ok"}

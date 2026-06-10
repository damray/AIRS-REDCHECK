from fastapi import FastAPI

from app.api import (
    datasets,
    evaluation_jobs,
    health,
    judge_prompt_profiles,
    mapping_profiles,
    portkey_gateway_profiles,
    projects,
    results,
)
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.include_router(health.router)
    app.include_router(mapping_profiles.router)
    app.include_router(portkey_gateway_profiles.router)
    app.include_router(judge_prompt_profiles.router)
    app.include_router(projects.router)
    app.include_router(evaluation_jobs.router)
    app.include_router(results.router)
    app.include_router(datasets.router)
    return app


app = create_app()

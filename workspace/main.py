import logging
import os

from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn
from workspace.configs.settings import settings
from workspace.configs.db_config import init_db
from workspace.rest.generator_controller import generator_router

log_level = os.getenv("LOG_LEVEL", settings.LOG_LEVEL).upper()

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="AI Microservice Starter", lifespan=lifespan)
app.include_router(generator_router)

if __name__ == "__main__":
    uvicorn.run(
        "workspace.main:app",
        host="0.0.0.0",
        port=getattr(settings, "SERVER_PORT", None) or settings.PORT,
        reload=True,
    )

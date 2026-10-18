import logging
import os

from fastapi import FastAPI
import uvicorn
from workspace.gen_rest_controller import generator_router
from workspace.settings import Settings

log_level = os.getenv(Settings.LOG_LEVEL, "INFO").upper()

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


app = FastAPI(title="AI Microservice Starter")
app.include_router(generator_router)

if __name__ == "__main__":
    uvicorn.run("workspace.main:app", host="0.0.0.0", port=Settings.PORT, reload=True)

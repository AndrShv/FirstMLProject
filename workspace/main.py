from fastapi import FastAPI
import uvicorn
from workspace.gen_rest_controller import generator_router

app = FastAPI(title="AI Microservice Starter")
app.include_router(generator_router)

if __name__ == "__main__":
    uvicorn.run("workspace.main:app", host="0.0.0.0", port=8000, reload=True)

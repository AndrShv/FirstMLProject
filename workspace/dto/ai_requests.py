from pydantic import BaseModel


class GeneratingRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 500
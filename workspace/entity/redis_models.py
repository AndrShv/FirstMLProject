from pydantic import BaseModel


class AiCache(BaseModel):
    request_key: str
    request: str
    response: str
    input_tokens: int
    output_tokens: int



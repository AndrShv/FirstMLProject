import logging

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


CLOUD_URL = "https://knox-exopoditic-azalea.ngrok-free.dev/generate-cloud"





def generate_text(prompt: str, max_new_tokens: int = 100) -> str:
    response = requests.post(
        CLOUD_URL,
        params={"prompt": prompt, "max_new_tokens": max_new_tokens}
    )
    if response.status_code == 200:
        data = response.json()
        return data["response"]
    else:
        raise Exception(f"Ошибка при обращении к облаку: {response.text}")

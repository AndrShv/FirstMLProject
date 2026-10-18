import logging
import requests

logger = logging.getLogger(__name__)
CLOUD_URL = "https://knox-exopoditic-azalea.ngrok-free.dev/generate-cloud"


def generate_text(prompt: str, max_new_tokens: int = 500) -> dict:
    try:
        response = requests.post(
            CLOUD_URL,
            json={"prompt": prompt, "max_new_tokens": max_new_tokens},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()

        if "response" not in data:
            raise KeyError(f"В ответе нет ключа 'response'. Доступные ключи: {list(data.keys())}")

        return {
            "response": data["response"],
            "input_tokens": data.get("prompt_tokens", len(prompt.split())),
            "output_tokens": data.get("completion_tokens", len(data["response"].split()))
        }

    except Exception as e:
        logger.error(f"Ошибка при запросе к модели: {e}")
        raise
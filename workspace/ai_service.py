import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

CLOUD_URL = "https://knox-exopoditic-azalea.ngrok-free.dev/generate-cloud"


def generate_text(prompt: str, max_new_tokens: int = 500) -> str | None:
    try:
        response = requests.post(
            CLOUD_URL,
            json={"prompt": prompt, "max_new_tokens": max_new_tokens},
            timeout=60  # ngrok + ML-модель могут отвечать долго
        )

        logger.info(f"Status: {response.status_code}")
        logger.info(f"Raw response text: {response.text[:500]}")  # первые 500 символов

        response.raise_for_status()  # бросит HTTPError при 4xx/5xx

        # Безопасный парсинг JSON
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as e:
            raise ValueError(
                f"Сервер вернул не JSON. "
                f"Content-Type: {response.headers.get('Content-Type')}. "
                f"Тело ответа: {response.text[:300]}"
            ) from e

        if "response" not in data:
            raise KeyError(
                f"В ответе нет ключа 'response'. "
                f"Доступные ключи: {list(data.keys())}. "
                f"Полный JSON: {data}"
            )

        return data["response"]

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Не удалось подключиться к серверу: {e}")
        raise
    except requests.exceptions.Timeout:
        logger.error("Таймаут — сервер не ответил вовремя")
        raise
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP ошибка: {e.response.status_code} — {e.response.text[:300]}")
        raise
    except (ValueError, KeyError) as e:
        logger.error(f"Ошибка обработки ответа: {e}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {type(e).__name__}: {e}")
        raise
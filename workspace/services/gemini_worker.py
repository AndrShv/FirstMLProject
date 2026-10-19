import asyncio
import json
import logging
from typing import Any

from google import genai
from workspace.configs.celery_cfg import celery_app
from workspace.configs.settings import settings
from workspace.dto.ai_requests import AiRequest
from workspace.helpers.cleaners import clean_json
from workspace.helpers.time_logger import count_latency

GEMINI_MODEL = "gemini-2.5-flash"
logger = logging.getLogger(__name__)


async def gemini_request(prompt: str, generated: str, reference: str) -> dict[Any, Any]:
    global e
    judge_prompt = f"""
    Оцени ответ, сгенерированный моделью, по сравнению с эталоном.
    Промпт: {prompt}
    Эталон (Ground Truth): {reference}
    Ответ модели: {generated}

    Дай оценку от 1 до 5 и краткое объяснение.
    ОТВЕТЬ СТРОГО В ФОРМАТЕ JSON (без markdown-оберток):
    {{"score": 5, "reason": "..."}}
    """
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=judge_prompt,
        )

        raw_text = response.text.strip()

        cleaned_text = await clean_json(raw_text)

        result = json.loads(cleaned_text)
        return {
            "score": int(result.get("score", 1)),
            "reason": result.get("reason", "Не удалось распарсить причину")
        }
    except Exception as e:
        logger.error(f"Ошибка при запросе к Gemini: {e}")
    return {
        "score": 1,
        "reason": f"Ошибка запроса: {str(e)}"
    }


@celery_app.task(name="workspace.worker.generating_method", bind=True)
@count_latency
def make_ai_request(self, data: AiRequest):
    try:
        asyncio.run(gemini_request(data.prompt, data.generated, data.reference))
    except Exception as e:
        self.retry(exc=e, countdown=60)

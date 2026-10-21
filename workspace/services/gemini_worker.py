import asyncio
import json
import logging
from typing import List, Any
from google import genai
from workspace.configs.settings import settings
from workspace.helpers.cleaners import clean_json

GEMINI_MODEL = "gemini-3.6-flash"
logger = logging.getLogger(__name__)


async def gemini_batch_request(batch_items: List[dict], max_retries: int = 3) -> None | list[dict[str, int | str]] | \
                                                                                 list[Any]:
    formatted_items = ""
    for idx, item in enumerate(batch_items, 1):
        formatted_items += f"""
---
Элемент #{idx}:
Промпт: {item['prompt']}
Эталон (Ground Truth): {item['reference']}
Ответ модели: {item['generated']}
"""

    judge_prompt = f"""
Ты строгий и объективный AI-судья. Оцени пачку ответов, сгенерированных локальной моделью, по сравнению с эталонами.
Для каждого элемента дай оценку от 1 до 5 и краткое объяснение.

{formatted_items}

ОТВЕТЬ СТРОГО В ВИДЕ JSON-МАССИВА (без markdown-оберток ```json ... ```, чистый массив):
[
  {{"index": 1, "score": 5, "reason": "..."}},
  {{"index": 2, "score": 3, "reason": "..."}}
]
"""

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    for attempt in range(1, max_retries + 1):
        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=judge_prompt,
            )

            raw_text = response.text.strip()
            cleaned_text = await clean_json(raw_text)

            result = json.loads(cleaned_text)

            evaluated_map = {}
            for res in result:
                idx = int(res.get("index", 0))
                evaluated_map[idx] = {
                    "score": int(res.get("score", 1)),
                    "reason": res.get("reason", "Не удалось распарсить причину")
                }

            final_results = []
            for i in range(1, len(batch_items) + 1):
                if i in evaluated_map:
                    final_results.append(evaluated_map[i])
                else:
                    final_results.append({"score": 1, "reason": "Пропущено в ответе судьи"})
            return final_results

        except Exception as e:
            logger.warning(f"Попытка {attempt}/{max_retries} не удалась: {e}")
            if attempt < max_retries:
                wait_time = attempt * 5
                logger.info(f"Ожидание {wait_time} секунд перед повторным запросом к Gemini...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Все попытки исчерпаны. Ошибка при пакетном запросе к Gemini: {e}")
                return [{"score": 1, "reason": f"Ошибка запроса батча (после {max_retries}): {str(e)}"} for _ in batch_items]

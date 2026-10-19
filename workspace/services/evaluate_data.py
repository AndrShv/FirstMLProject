import asyncio
import json
import logging
from pathlib import Path
from celery.result import AsyncResult
from workspace.configs.celery_cfg import celery_app
from workspace.services.gemini_worker import gemini_request
from workspace.services.worker import generating_method

logger = logging.getLogger(__name__)
DATASET_PATH = Path(__file__).resolve().parents[2] / "dataset_for_training.json"
REPORT_PATH = Path(__file__).resolve().parents[2] / "eval_report.json"



async def evaluate():
    try:
        with DATASET_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error("Файл dataset_for_training.json не найден: %s", DATASET_PATH)
        return {"result": [], "error": "Файл dataset_for_training.json не найден"}

    results = []
    avg_score = None

    for idx, item in enumerate(data, 1):
        prompt = item.get("prompt") or item.get("instruction")
        ground_truth = item.get("ground_truth") or item.get("output")

        if not prompt or not ground_truth:
            print(f"[{idx}] Пропуск: не найден prompt или ground_truth в элементе.")
            continue

        print(f"[{idx}/{len(data)}] Отправка промпта: {prompt}")

        try:
            task = generating_method.delay(prompt, 300)
        except Exception as e:
            print(f"Ошибка постановки задачи в Celery: {e}")
            continue

        generated_text = None
        for _ in range(30):
            await asyncio.sleep(1)
            try:
                task_result = AsyncResult(task.id, app=celery_app)
                if task_result.successful():
                    generated_text = task_result.result
                    break
                elif task_result.failed():
                    print(f"Задача в воркере завершилась с ошибкой: {task_result.result}")
                    break
            except Exception:
                pass

        if not generated_text:
            print(f"Таймаут выполнения для промпта: {prompt}")
            continue

        print("Оценка ответа через Gemini-судью...")
        evaluation = await gemini_request(prompt, generated_text, ground_truth)

        results.append({
            "prompt": prompt,
            "generated": generated_text,
            "ground_truth": ground_truth,
            "score": evaluation["score"],
            "reason": evaluation["reason"]
        })
        print(f"Оценка: {evaluation['score']}/5 | Причина: {evaluation['reason']}\n")

    if results:
        avg_score = sum(r["score"] for r in results) / len(results)
        print(f"\n=== ИТОГОВЫЙ БЕНЧМАРК ===")
        print(f"Средний балл качества: {avg_score:.2f} / 5.0")

    with REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print("Отчет сохранен в eval_report.json")
    return {
        "result": results,
        "count": len(results),
        "average_score": avg_score if results else None,
    }

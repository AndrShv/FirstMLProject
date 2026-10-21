import asyncio
import json
import logging
from pathlib import Path
from celery.result import AsyncResult
from workspace.configs.celery_cfg import celery_app
from workspace.services.gemini_worker import gemini_batch_request
from workspace.services.worker import generating_method

logger = logging.getLogger(__name__)
DATASET_PATH = Path(__file__).resolve().parents[2] / "dataset_for_training.json"
REPORT_PATH = Path(__file__).resolve().parents[2] / "eval_report.json"
BATCH_SIZE = 10



async def evaluate():
    try:
        with DATASET_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error("Файл dataset_for_training.json не найден: %s", DATASET_PATH)
        return {"result": [], "error": "Файл dataset_for_training.json не найден"}

    results = []
    avg_score = None

    valid_items = []
    for idx, item in enumerate(data, 1):
        prompt = item.get("prompt") or item.get("instruction")
        ground_truth = item.get("ground_truth") or item.get("output")
        if not prompt or not ground_truth:
            print(f"[{idx}] Пропуск: не найден prompt или ground_truth в элементе.")
            continue
        valid_items.append({"prompt": prompt, "reference": ground_truth})

    for batch_start in range(0, len(valid_items), BATCH_SIZE):
        batch = valid_items[batch_start:batch_start + BATCH_SIZE]
        print(f"\nПачка {batch_start // BATCH_SIZE + 1}: отправка {len(batch)} запросов в локальный ИИ")

        tasks = []
        for item in batch:
            print(f"Отправка промпта: {item['prompt']}")
            try:
                tasks.append(generating_method.delay(item["prompt"], 300))
            except Exception as e:
                print(f"Ошибка постановки задачи в Celery: {e}")
                tasks.append(None)

        generated_items = []
        pending = {task.id: (position, task) for position, task in enumerate(tasks) if task}
        for _ in range(30):
            await asyncio.sleep(1)
            for task_id, (position, task) in list(pending.items()):
                try:
                    task_result = AsyncResult(task_id, app=celery_app)
                    if task_result.successful():
                        if task_result.result:
                            batch[position]["generated"] = task_result.result
                            generated_items.append(batch[position])
                        del pending[task_id]
                    elif task_result.failed():
                        print(f"Задача завершилась с ошибкой: {task_result.result}")
                        del pending[task_id]
                except Exception as e:
                    print(f"Ошибка проверки задачи {task_id}: {e}")
            if not pending:
                break

        if pending:
            print(f"Таймаут: {len(pending)} задач локального ИИ")

        if not generated_items:
            continue

        print(f"Оценка пачки из {len(generated_items)} ответов одним запросом через Gemini-судью...")
        evaluations = await gemini_batch_request(generated_items)
        for item, evaluation in zip(generated_items, evaluations):
            results.append({
                "prompt": item["prompt"],
                "generated": item["generated"],
                "ground_truth": item["reference"],
                "score": evaluation["score"],
                "reason": evaluation["reason"]
            })
            print(f"Оценка: {evaluation['score']}/5 | Причина: {evaluation['reason']}")

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

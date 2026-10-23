# Структура проекта

```text
workspace/
├── main.py                         # FastAPI-приложение
├── configs/                        # Конфигурация приложения и Celery
├── dto/ai_requests.py              # DTO запросов к AI
├── entity/                         # Модели базы данных и Redis
├── helpers/                        # Вспомогательные функции
├── repo/output_repo.py             # Работа с результатами
├── rest/generator_controller.py    # HTTP endpoints
└── services/
    ├── ai_cache_service.py         # Кэш AI-ответов
    ├── ai_service.py               # Запросы worker в Colab
    ├── evaluate_data.py            # Оценка датасета
    ├── gemini_worker.py            # Вызов Gemini-судьи
    └── worker.py                   # Celery-задачи

Dockerfile                          # Образ приложения
docker-compose.yml                  # RabbitMQ и worker
requirements.txt                    # Python-зависимости
dataset_for_training.json           # Датасет
train.jsonl                         # Данные для обучения
eval_report.json                    # Отчёт оценки
```

Поток обработки запроса:

```text
Клиент → workspace.main → generator_controller
       → RabbitMQ → services.worker → services.ai_service → Colab/vLLM
```

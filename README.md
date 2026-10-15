# AI Microservice Starter

Небольшой микросервис на FastAPI и Celery. API принимает запрос на генерацию ключа в заданном диапазоне, а Celery worker выполняет задачу асинхронно через RabbitMQ.

## Структура проекта

```text
workspace/
├── main.py                 # FastAPI-приложение
├── gen_rest_controller.py  # HTTP endpoints
├── celery_cfg.py           # Конфигурация Celery
└── worker.py               # Celery-задача
Dockerfile
docker-compose.yml         # RabbitMQ и Celery worker
requirements.txt
```

## Запуск

### Вариант 1: Docker Compose

Запустите RabbitMQ и Celery worker:

```bash
docker compose up --build
```

RabbitMQ Management UI будет доступен по адресу http://localhost:15672.

Параметры по умолчанию: `guest` / `guest`.

Затем запустите FastAPI локально:

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn workspace.main:app --reload --host 0.0.0.0 --port 8000
```

При локальном запуске API должен использовать RabbitMQ на `localhost:5672`. Это значение задано по умолчанию в `workspace/celery_cfg.py`.

### Вариант 2: локальный Celery worker

Если RabbitMQ уже запущен локально, worker можно запустить напрямую:

```bash
celery -A workspace.celery_cfg:celery_app worker --loglevel=info
```

## API

Документация Swagger: http://localhost:8000/docs

### Создать задачу

```bash
curl -X POST "http://localhost:8000/generate?prompt=a%20new%20key&start=1&end=1000"
```

Ответ содержит `task_id`:

```json
{
  "status": "queued",
  "prompt": "a new key",
  "task_id": "<task-id>",
  "detail": "Task has been accepted for processing by Celery worker."
}
```

### Проверить статус

Подставьте полученный идентификатор задачи:

```bash
curl "http://localhost:8000/task_status/<task-id>"
```

Возможные статусы: `Pending`, `completed` и `failed`.

## Переменные окружения

Для подключения к RabbitMQ можно задать URL брокера:

```bash
export CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
```

В Docker Compose worker автоматически использует адрес RabbitMQ-контейнера.

## Проверка

Проверка синтаксиса исходников:

```bash
python -m compileall workspace
```

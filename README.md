# AI Microservice Starter — Hybrid Cloud GPU

Гибридный микросервис для генерации текста: локально работают FastAPI, RabbitMQ и Celery worker, а модель `Qwen/Qwen2.5-3B-Instruct` с вашим собственным LoRA-адаптером (`docker_adapter`) запускается на GPU T4 в Google Colab. Worker обращается к Colab через безопасный HTTPS-туннель ngrok.

```text
Клиент → FastAPI :8000 → RabbitMQ :5672 → Celery worker
                                      ↓ HTTPS через ngrok
                              Google Colab + T4 GPU (vLLM + LoRA)
```

Локальный компьютер принимает запросы и управляет очередью задач, но не хранит тяжелые веса модели и не выполняет ресурсоемкий инференс.

Подробное объяснение процесса обучения, LoRA/QLoRA и инференса находится в [TRAINING_EXPLANATION.md](TRAINING_EXPLANATION.md).

## Структура проекта

```text
workspace/
├── __init__.py
├── main.py                       # Главное FastAPI-приложение
├── rest/
│   └── generator_controller.py   # HTTP-запросы и логика бенчмарка
├── celery_cfg.py                 # Конфигурация брокера Celery
├── worker.py                     # Асинхронная Celery-задача
└── services/
    ├── ai_service.py             # HTTP-клиент Google Colab через ngrok
    └── gemini_worker.py          # Gemini-судья пакетной оценки
Dockerfile
docker-compose.yml
requirements.txt
eval_report.json                  # Отчёт оценки качества ответов
```

## Описание компонентов проекта

### 1. Инфраструктура и оркестрация

`Dockerfile` и `docker-compose.yml` описывают изоляцию локальной среды, сборку приложения и запуск RabbitMQ, через который асинхронно координируются задачи.

`requirements.txt` содержит локальные Python-зависимости: FastAPI, Celery, Pydantic, Requests, Google GenAI SDK и другие.

### 2. Локальное приложение и задачи (`workspace/`)

`main.py` — точка входа локального FastAPI-сервиса. Запускает сервер на порту 8000 и подключает маршруты.

`rest/generator_controller.py` обрабатывает HTTP-вызовы клиентов. Реализует эндпоинт пакетной оценки `/assesment`, который разбивает датасет на пачки, параллельно ставит задачи в очередь и отправляет их на судейство.

`celery_cfg.py` настраивает подключение Celery к RabbitMQ: `amqp://guest:guest@rabbitmq:5672//`.

`worker.py` содержит фоновую Celery-задачу, которая принимает промпт и передаёт его в облачный сервис.

`services/ai_service.py` выполняет HTTP POST-запросы на публичный ngrok URL Google Colab, где запущена модель.

`services/gemini_worker.py` отправляет пачки ответов локальной модели в Gemini Flash для объективной оценки по шкале от 1 до 5 с подробным обоснованием.

## Порядок запуска системы

1. Запустите Google Colab, используя второй файл с кодом для Colab, и получите актуальный ngrok URL:

   `https://xxxx.ngrok-free.dev/generate-cloud`

2. Обновите `workspace/services/ai_service.py`, прописав туда полученный ngrok URL.

3. Запустите RabbitMQ и worker локально через Docker Compose:

   ```bash
   docker compose up --build
   ```

4. Запустите локальный FastAPI:

   ```bash
   uvicorn workspace.main:app --reload --host 0.0.0.0 --port 8000
   ```

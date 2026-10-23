# AI Microservice Starter — Hybrid Cloud GPU

Гибридный микросервис для генерации текста. FastAPI, RabbitMQ и Celery worker работают локально, а модель запускается на GPU T4 в Google Colab через HTTPS-туннель ngrok.

```text
Клиент → FastAPI :8000 → RabbitMQ :5672 → Celery worker
                                      ↓ HTTPS через ngrok
                              Google Colab + T4 GPU
```

Локальный компьютер принимает запросы и управляет очередью, но не хранит веса модели и не выполняет инференс.

Структура проекта вынесена в [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md), а кодовые фрагменты — в [README_CODE.md](README_CODE.md).

## Безопасность ngrok-токена

Не записывайте токен в Git, README или публичную ячейку Colab. В Colab откройте **Secrets** и создайте secret `NGROK_AUTHTOKEN`.

## Запуск

После каждого перезапуска Google Colab выберите **Runtime → Change runtime type → T4 GPU**, установите зависимости и запустите код из [README_CODE.md](README_CODE.md). Скопируйте новый URL ngrok с endpoint `/generate-cloud` в `workspace/services/ai_service.py`.

Запустите RabbitMQ и worker:

```bash
docker compose up --build
```

В новом терминале запустите FastAPI:

```bash
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn workspace.main:app --reload --host 0.0.0.0 --port 8000
```

RabbitMQ Management UI: http://localhost:15672 (`guest` / `guest`). Swagger: http://localhost:8000/docs.

Если менялся только URL Colab:

```bash
docker compose restart worker
```

## API

Создать задачу:

```bash
curl -X POST "http://localhost:8000/generate?prompt=a%20new%20key&max_new_tokens=50"
```

Проверить статус:

```bash
curl "http://localhost:8000/task/<task-id>"
```

Статусы Celery: `PENDING`, `STARTED`, `SUCCESS`, `FAILURE`. При успехе результат находится в поле `result`.

## Пакетная оценка датасета

```bash
curl "http://localhost:8000/assesment"
```

Оценка выполняется пачками по 10 элементов: задачи отправляются в Celery параллельно, ответы объединяются и передаются Gemini-судье. Отчёт сохраняется в `eval_report.json`.

Модель судьи задаётся в `workspace/services/gemini_worker.py` через `GEMINI_MODEL`. Для работы требуется `GEMINI_API_KEY`. Ошибка `503 UNAVAILABLE` означает временную перегрузку Gemini, а не оценку `1/5`.

## Остановка и проверка

```bash
docker compose down
python -m compileall workspace
curl http://localhost:8000/
```

При следующем запуске Colab снова загрузите модель, получите новый ngrok URL, обновите `workspace/services/ai_service.py` и перезапустите worker.

# AI Microservice Starter — Hybrid Cloud GPU

Гибридный микросервис для генерации текста: локально работают FastAPI, RabbitMQ и Celery worker, а модель `Qwen/Qwen2.5-0.5B-Instruct` запускается на GPU T4 в Google Colab. Worker обращается к Colab через HTTPS-туннель ngrok.

```text
Клиент → FastAPI :8000 → RabbitMQ :5672 → Celery worker
                                      ↓ HTTPS через ngrok
                              Google Colab + T4 GPU
```

Локальный компьютер принимает запросы и управляет очередью, но не хранит веса модели и не выполняет инференс.

## Структура проекта

```text
workspace/
├── main.py                 # FastAPI-приложение
├── gen_rest_controller.py  # HTTP endpoints
├── celery_cfg.py           # Конфигурация Celery
├── worker.py               # Celery-задача
└── ai_service.py           # HTTP-запрос из worker в Colab
Dockerfile
docker-compose.yml
requirements.txt
```

## Важно: безопасность ngrok-токена

Токен ngrok был опубликован в сообщении. Считайте его скомпрометированным: отзовите его в [личном кабинете ngrok](https://dashboard.ngrok.com/get-started/your-authtoken) и создайте новый.

Не записывайте токен в Git, README или публичную ячейку Colab. В Colab откройте **Secrets** и создайте secret `NGROK_AUTHTOKEN`, затем используйте:

```python
from google.colab import userdata
from pyngrok import ngrok

ngrok.set_auth_token(userdata.get("NGROK_AUTHTOKEN"))
```

## Запуск после перезапуска Google Colab

После остановки или нового запуска Colab старый GPU-процесс и старый ngrok URL обычно недействительны. Каждый раз выполняйте следующие шаги.

### 1. Запустите Colab GPU

1. Откройте notebook.
2. Выберите **Runtime → Change runtime type → T4 GPU**.
3. Выполните ячейку установки:

```python
!pip install -q fastapi uvicorn transformers torch accelerate pyngrok
```

4. Выполните код из раздела [Код Colab](#код-colab).
5. Дождитесь загрузки модели и скопируйте напечатанный URL вида `https://xxxx.ngrok-free.dev`.

Не закрывайте эту Colab-сессию: ячейка с сервером должна оставаться активной.

### 2. Обновите URL в локальном проекте

В `workspace/ai_service.py` замените URL на новый адрес Colab с endpoint `/generate-cloud`:

```python
CLOUD_URL = "https://xxxx.ngrok-free.dev/generate-cloud"
```

После изменения URL перезапустите Celery worker.

### 3. Запустите RabbitMQ и worker

В корне проекта:

```bash
docker compose up --build
```

RabbitMQ Management UI: http://localhost:15672 (`guest` / `guest`).

Если контейнеры уже собраны и менялся только URL Colab:

```bash
docker compose restart worker
```

### 4. Запустите локальный FastAPI

В новом терминале:

```bash
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn workspace.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger: http://localhost:8000/docs

## API

Создать задачу:

```bash
curl -X POST "http://localhost:8000/generate?prompt=a%20new%20key&max_new_tokens=50"
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

Проверить статус:

```bash
curl "http://localhost:8000/task_status/<task-id>"
```

Статусы: `Pending`, `completed`, `failed`. При успешном выполнении результат находится в поле `result`.

## Код Colab

Сначала выполните ячейку установки зависимостей, затем этот код:

```python
import threading

import torch
import uvicorn
from fastapi import FastAPI
from google.colab import userdata
from pyngrok import ngrok
from transformers import AutoModelForCausalLM, AutoTokenizer

token = userdata.get("NGROK_AUTHTOKEN")
if not token:
    raise RuntimeError("Создайте Colab Secret NGROK_AUTHTOKEN")
ngrok.set_auth_token(token)

app = FastAPI(title="Colab AI Inference Node")
model_name = "Qwen/Qwen2.5-0.5B-Instruct"

print("⏳ Загружаем модель на GPU в Google Colab...")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto",
)
print("✅ Модель успешно загружена на GPU!")

@app.post("/generate-cloud")
def cloud_generate(prompt: str, max_new_tokens: int = 100):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
        )
    return {
        "prompt": prompt,
        "response": tokenizer.decode(outputs[0], skip_special_tokens=True),
    }

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=5000)

threading.Thread(target=run_server, daemon=True).start()
public_url = ngrok.connect(5000)
print("🚀 Cloud AI server is running")
print(f"👉 {public_url}/generate-cloud")
```

## Переменные окружения

Локальный RabbitMQ по умолчанию:

```bash
export CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
```

В Docker Compose worker подключается к RabbitMQ по адресу контейнера `rabbitmq`.

## Остановка и следующий запуск

Остановить локальные контейнеры:

```bash
docker compose down
```

При следующем запуске Colab снова загрузите модель, получите новый ngrok URL, обновите `workspace/ai_service.py` и перезапустите worker.

Проверить проект:

```bash
python -m compileall workspace
curl http://localhost:8000/
```

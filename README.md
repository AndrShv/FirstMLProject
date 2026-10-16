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
import subprocess
import time
import threading
import traceback
import requests
import uvicorn
import os
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pyngrok import ngrok

# === Чистим старые процессы ===
os.system("pkill -9 -f uvicorn")
os.system("pkill -9 -f vllm")
ngrok.kill()
time.sleep(3)

NGROK_TOKEN = "3Bso9CD8XDewe5wRxdNSLmBF0EW_VxeqzyfAhuGm4Zkt8zt7"
ngrok.set_auth_token(NGROK_TOKEN)

VLLM_PORT = 8001
WRAPPER_PORT = 5002
model_name = "Qwen/Qwen2.5-0.5B-Instruct"

# === Запуск vLLM ===
print(f"⏳ Запускаем vLLM на порту {VLLM_PORT}...")
vllm_process = subprocess.Popen(
    [
        "python3", "-m", "vllm.entrypoints.openai.api_server",
        "--model", model_name,
        "--port", str(VLLM_PORT),
        "--dtype", "float16"
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

def stream_vllm_logs():
    for line in vllm_process.stdout:
        print(f"[vLLM] {line}", end="")

threading.Thread(target=stream_vllm_logs, daemon=True).start()

# === Ждём готовности vLLM ===
start = time.time()
while time.time() - start < 300:
    if vllm_process.poll() is not None:
        print(f"\n❌ vLLM упал с кодом: {vllm_process.returncode}")
        sys.exit(1)
    try:
        r = requests.get(f"http://localhost:{VLLM_PORT}/health", timeout=2)
        if r.status_code == 200:
            print(f"\n✅ vLLM готов на порту {VLLM_PORT}!")
            break
    except requests.exceptions.ConnectionError:
        pass
    time.sleep(5)
else:
    print("❌ Таймаут")
    vllm_process.kill()
    sys.exit(1)

# === FastAPI wrapper ===
app = FastAPI(title="Colab AI Wrapper")

class GenerationRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 100

@app.post("/generate-cloud")
def cloud_generate(req: GenerationRequest):
    try:
        response = requests.post(
            f"http://localhost:{VLLM_PORT}/v1/chat/completions",
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": req.prompt}],
                "max_tokens": req.max_new_tokens,
                "temperature": 0.7
            },
            timeout=60
        )
        if response.status_code != 200:
            raise Exception(f"vLLM error {response.status_code}: {response.text}")

        answer = response.json()["choices"][0]["message"]["content"]
        return {"prompt": req.prompt, "response": answer}

    except Exception as e:
        print("❌ Ошибка:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=WRAPPER_PORT, log_level="warning")

threading.Thread(target=run_server, daemon=True).start()
time.sleep(2)

# === ngrok туннель ===
public_url = ngrok.connect(WRAPPER_PORT)
new_cloud_url = f"{public_url.public_url}/generate-cloud"

print("🚀 Всё запущено!")
print(f"👉 СКОПИРУЙ В ai_service.py:\n{new_cloud_url}")
```



```python
import os
import time
import subprocess

# Убиваем всё что держит GPU
os.system("fuser -k /dev/nvidia0")
os.system("fuser -k /dev/nvidiactl")
os.system("pkill -9 -f vllm")
time.sleep(3)

# Проверяем что VRAM освободилась
result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
print(result.stdout)
```

```python
import subprocess
result = subprocess.run(['fuser', '-v', '/dev/nvidia0'], capture_output=True, text=True)
print(result.stderr)  # покажет PID процессов на GPU
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

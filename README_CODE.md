# Код

Кодовые фрагменты из исходного README собраны здесь. Пояснения и порядок запуска находятся в [README.md](README.md).

## Секрет и установка в Colab

```python
from google.colab import userdata
from pyngrok import ngrok

ngrok.set_auth_token(userdata.get("NGROK_AUTHTOKEN"))
```

```python
!pip install -q fastapi uvicorn transformers torch accelerate pyngrok vllm
```

## URL Colab в локальном сервисе

```python
CLOUD_URL = "https://xxxx.ngrok-free.dev/generate-cloud"
```

## Основной сервер Colab: vLLM + FastAPI + ngrok

```python
import subprocess, time, threading, traceback, requests, uvicorn, os, sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pyngrok import ngrok
from google.colab import userdata

os.system("pkill -9 -f uvicorn")
os.system("pkill -9 -f vllm")
ngrok.kill()
time.sleep(3)
ngrok.set_auth_token(userdata.get("NGROK_AUTHTOKEN"))

VLLM_PORT = 8001
WRAPPER_PORT = 5002
model_name = "Qwen/Qwen2.5-0.5B-Instruct"

vllm_process = subprocess.Popen(
    ["python3", "-m", "vllm.entrypoints.openai.api_server",
     "--model", model_name, "--port", str(VLLM_PORT), "--dtype", "float16"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

def stream_vllm_logs():
    for line in vllm_process.stdout:
        print(f"[vLLM] {line}", end="")

threading.Thread(target=stream_vllm_logs, daemon=True).start()
start = time.time()
while time.time() - start < 300:
    if vllm_process.poll() is not None:
        sys.exit(1)
    try:
        if requests.get(f"http://localhost:{VLLM_PORT}/health", timeout=2).status_code == 200:
            break
    except requests.exceptions.ConnectionError:
        pass
    time.sleep(5)
else:
    vllm_process.kill()
    sys.exit(1)

app = FastAPI(title="Colab AI Wrapper")

class GenerationRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 100

@app.post("/generate-cloud")
def cloud_generate(req: GenerationRequest):
    try:
        response = requests.post(
            f"http://localhost:{VLLM_PORT}/v1/chat/completions",
            json={"model": model_name,
                  "messages": [{"role": "user", "content": req.prompt}],
                  "max_tokens": req.max_new_tokens, "temperature": 0.7},
            timeout=60)
        if response.status_code != 200:
            raise Exception(f"vLLM error {response.status_code}: {response.text}")
        return {"prompt": req.prompt,
                "response": response.json()["choices"][0]["message"]["content"]}
    except Exception as e:
        print("❌ Ошибка:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=WRAPPER_PORT, log_level="warning")

threading.Thread(target=run_server, daemon=True).start()
time.sleep(2)
public_url = ngrok.connect(WRAPPER_PORT)
print(f"👉 СКОПИРУЙ В ai_service.py:\n{public_url.public_url}/generate-cloud")
```

## Освобождение GPU в Colab

```python
import os, time, subprocess
os.system("fuser -k /dev/nvidia0")
os.system("fuser -k /dev/nvidiactl")
os.system("pkill -9 -f vllm")
time.sleep(3)
print(subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout)
print(subprocess.run(["fuser", "-v", "/dev/nvidia0"], capture_output=True, text=True).stderr)
```

## QLoRA

Для обучения и запуска LoRA-адаптера используйте Colab-блоки из исходного README: установка `transformers`, `datasets`, `trl`, `peft`, загрузка `Qwen/Qwen2.5-3B-Instruct`, `SFTTrainer`, сохранение адаптера и запуск vLLM с `--enable-lora`.

Файл: colab_scripts_and_guide.md — Скрипты для Google Colab и руководство
Этот документ содержит полный набор готовых скриптов для выполнения в Google Colab (T4 GPU), а также подробные объяснения назначения каждого скрипта.

Скрипт 1: Обучение QLoRA-адаптера для 3B модели
Назначение: Загружает базовую языковую модель Qwen/Qwen2.5-3B-Instruct, подготавливает датасет из загруженного локально файла train.jsonl и выполняет дообучение методом QLoRA (3 эпохи) с сохранением адаптера в локальную папку ./my_docker_lora_adapter_3b.

```python
!pip install -q torch transformers datasets trl peft bitsandbytes accelerate
!pip install -U torchao
import os

os.environ["WANDB_DISABLED"] = "true"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import sys

for mod in list(sys.modules.keys()):
  if "wandb" in mod:
    del sys.modules[mod]

import torch
from datasets import load_dataset
from google.colab import files
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

print("Пожалуйста, выберите файл train.jsonl на вашем компьютере:")
uploaded = files.upload()
filename = list(uploaded.keys())[0]

MODEL_ID = "Qwen/Qwen2.5-3B-Instruct"

print("Загружаем токенизатор и модель...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,
    device_map="cuda:0",
    trust_remote_code=True,
)

peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

dataset = load_dataset("json", data_files=filename, split="train")

training_args = SFTConfig(
    output_dir="./results_qlora_3b",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    logging_steps=1,
    num_train_epochs=3,
    save_strategy="epoch",
    fp16=True,
    bf16=False,
    optim="adamw_torch",
    max_length=512,
    report_to="none",
)

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    peft_config=peft_config,
    processing_class=tokenizer,
    args=training_args,
)

print("Запуск обучения QLoRA для 3B модели...")
trainer.train()

adapter_path = "./my_docker_lora_adapter_3b"
trainer.model.save_pretrained(adapter_path)
tokenizer.save_pretrained(adapter_path)
print(f"Готово! Адаптер сохранен в папку {adapter_path}")
```






Скрипт 2: Локальная проверка генерации (тест адаптера)
Назначение: Позволяет быстро проверить работу дообученной модели прямо внутри Colab перед поднятием REST-сервера. Загружает базу, навешивает сохраненный LoRA-адаптер и делает тестовый инференс.

```python
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "Qwen/Qwen2.5-3B-Instruct"
ADAPTER_PATH = "./my_docker_lora_adapter_3b"

print("Загружаем базовую модель и токенизатор...")
tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH)
base_model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, torch_dtype=torch.float16, device_map="cuda:0", trust_remote_code=True
)

print("Подключаем твой LoRA-адаптер...")
model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)

prompt = (
    "System: Ты опытный DevOps-инженер.\nUser: Как написать Dockerfile для FastAPI"
    " приложения с Poetry?"
)

inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

print("Генерируем ответ модели...")
outputs = model.generate(
    **inputs,
    max_new_tokens=256,
    temperature=0.7,
    top_p=0.9,
    do_sample=True,
    pad_token_id=tokenizer.eos_token_id,
)

response = tokenizer.decode(outputs[0], skip_special_tokens=True)
print("\n--- ОТВЕТ ОБУЧЕННОЙ МОДЕЛИ ---")
print(response)
```

Скрипт 3: Полный деплой-скрипт (vLLM + FastAPI Wrapper + ngrok)
Назначение: Основной рабочий скрипт для Colab.  {
Жестко очищает старые процессы и освобождает видеопамять (VRAM).
Запускает высокопроизводительный OpenAI-совместимый сервер vLLM на порту 8001 с активированной поддержкой LoRA-модуля (--enable-lora, --lora-modules).
Поднимает вспомогательный FastAPI-оберточный сервис на порту 5002 с эндпоинтом /generate-cloud.
Создает публичный ngrok-туннель, выдавая готовый URL, который нужно прописать в локальный проект.
}



```python
import os
import subprocess
import sys
import threading
import time
import requests
import uvicorn
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pyngrok import ngrok

# === Жесткая очистка GPU и процессов перед запуском ===
os.system("pkill -9 -f uvicorn")
os.system("pkill -9 -f vllm")
os.system("fuser -k /dev/nvidia0")
ngrok.kill()
time.sleep(3)

# Настройка ngrok токена
NGROK_TOKEN = "3Bso9CD8XDewe5wRxdNSLmBF0EW_VxeqzyfAhuGm4Zkt8zt7"
try:
    ngrok.set_auth_token(NGROK_TOKEN)
except Exception:
    pass

VLLM_PORT = 8001
WRAPPER_PORT = 5002

base_model_name = "Qwen/Qwen2.5-3B-Instruct"
adapter_path = os.path.abspath("./my_docker_lora_adapter_3b")
lora_model_id = "docker_adapter"

# Проверка наличия обученного адаптера на диске
if not os.path.exists(os.path.join(adapter_path, "adapter_config.json")):
    print(f"❌ ОШИБКА: Папка адаптера не найдена или пуста по пути: {adapter_path}")
    print("⚠️ Сначала запусти ячейку с обучением QLoRA в начале блокнота!")
    sys.exit(1)

print(f"⏳ Запускаем vLLM для 3B модели с адаптером из {adapter_path}...")
vllm_process = subprocess.Popen(
    [
        "python3",
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model", base_model_name,
        "--port", str(VLLM_PORT),
        "--dtype", "float16",
        "--gpu-memory-utilization", "0.80",  # Оптимизация памяти под ограничения T4 GPU
        "--enable-lora",                    # Включаем поддержку динамических LoRA-адаптеров
        "--lora-modules", f"{lora_model_id}={adapter_path}",
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

# === Ожидание полной готовности vLLM ===
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
    print("❌ Таймаут ожидания запуска vLLM")
    vllm_process.kill()
    sys.exit(1)

# === FastAPI Wrapper для приема запросов от локального воркера ===
app = FastAPI(title="Colab AI Wrapper")

class GenerationRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 512

@app.post("/generate-cloud")
def cloud_generate(req: GenerationRequest):
    try:
        response = requests.post(
            f"http://localhost:{VLLM_PORT}/v1/chat/completions",
            json={
                "model": lora_model_id,
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
        print("❌ Ошибка при генерации:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=WRAPPER_PORT, log_level="warning")

threading.Thread(target=run_server, daemon=True).start()
time.sleep(2)

# === Создание ngrok туннеля ===
public_url = ngrok.connect(WRAPPER_PORT)
new_cloud_url = f"{public_url.public_url}/generate-cloud"

print("🚀 Всё запущено!")
print(f"👉 СКОПИРУЙ В ai_service.py:\n{new_cloud_url}")
```

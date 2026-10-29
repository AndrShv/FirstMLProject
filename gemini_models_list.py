from google import genai
from workspace.configs.settings import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)
for model in client.models.list():
    print(f"Имя модели: {model.name}")
    if hasattr(model, 'supported_generation_methods'):
        print(f"Поддерживаемые методы: {model.supported_generation_methods}")
    print("-" * 40)
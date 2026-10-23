import json
from pathlib import Path

input_path = Path("/Users/andrshv/PycharmProjects/FirstMLProject/dataset_for_training.json")
output_path = Path("/Users/andrshv/PycharmProjects/FirstMLProject/train.jsonl")

with open(input_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Загружено {len(data)} примеров из {input_path}")

with open(output_path, "w", encoding="utf-8") as out_f:
    for item in data:
        prompt = item.get("prompt") or item.get("instruction")
        ground_truth = item.get("ground_truth") or item.get("output")

        if not prompt or not ground_truth:
            continue

        conversation = {
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": ground_truth}
            ]
        }

        out_f.write(json.dumps(conversation, ensure_ascii=False) + "\n")

print(f"Датасет успешно конвертирован и сохранен в {output_path}")
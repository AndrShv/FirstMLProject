async def clean_json(ai_answer: str) -> str:
    raw_text = ai_answer.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()
    new_text = raw_text.strip()

    return new_text

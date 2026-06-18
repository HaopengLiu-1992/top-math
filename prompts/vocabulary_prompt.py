import json


def system_prompt() -> str:
    return """You generate Grade 5-8 math/science academic vocabulary practice.
Output ONLY valid JSON. No markdown, no explanation.
Use simple English suitable for an English learner.
Make every example sentence useful for understanding math or science word problems."""


def user_prompt(date_str: str, grade_level: int, new_words: list[dict], review_words: list[dict]) -> str:
    return f"""Generate today's academic vocabulary task.

Date: {date_str}
Grade level: {grade_level}
New words:
{json.dumps(new_words, indent=2, ensure_ascii=False)}

Review words:
{json.dumps(review_words, indent=2, ensure_ascii=False)}

Return EXACTLY this JSON shape:
{{
  "date": "{date_str}",
  "subject": "english",
  "task_type": "vocabulary",
  "grade_level": {grade_level},
  "title": "Math & Science Academic Vocabulary",
  "estimated_minutes": 25,
  "words": [
    {{
      "id": "v_001",
      "word": "quotient",
      "category": "math_operations",
      "chinese": "商",
      "definition": "the answer to a division problem",
      "example": "The quotient of 42 divided by 6 is 7.",
      "quick_check": "What is the quotient of 35 divided by 5?",
      "answer": "7",
      "is_review": false
    }}
  ],
  "practice": {{
    "matching": [
      {{"id": "m_001", "word": "quotient", "definition": "the answer to a division problem"}}
    ],
    "fill_blank": [
      {{"id": "f_001", "sentence": "The ___ of 35 divided by 5 is 7.", "answer": "quotient"}}
    ],
    "keyword_reading": [
      {{
        "id": "k_001",
        "question": "A rectangle has a length of 8 cm and a width of 3 cm. Find its area.",
        "keyword": "area",
        "meaning": "the space inside a flat shape"
      }}
    ]
  }}
}}

Rules:
- Include every provided new word and review word exactly once in words.
- Use 15 new words and 5 review words when available; if fewer review words are provided, use more new words.
- matching must contain 10 items.
- fill_blank must contain 10 items.
- keyword_reading must contain 3 short math/science reading questions.
- Keep examples concise.
- If a provided Chinese or definition field is blank, fill it with a concise accurate value.
- Prefer math/science/academic meaning when a word has multiple meanings."""

import json


def system_prompt() -> str:
    return """You generate Grade 5-8 math/science academic vocabulary practice.
Output ONLY valid JSON. No markdown, no explanation.
Use simple English suitable for an English learner.
Make every example sentence useful for understanding math or science word problems."""


def user_prompt(date_str: str, grade_level: int, new_words: list[dict], review_words: list[dict],
                personal_prompt: str = "") -> str:
    personal_section = ""
    if personal_prompt.strip():
        personal_section = f"""

Personal prompt from the learner or parent:
{personal_prompt.strip()}
Treat this as a learner preference and follow it when compatible with the
grade level, vocabulary task structure, and required output format.
"""

    return f"""Generate today's academic vocabulary task.

Date: {date_str}
Grade level: {grade_level}
New words:
{json.dumps(new_words, indent=2, ensure_ascii=False)}

Review words:
{json.dumps(review_words, indent=2, ensure_ascii=False)}

The local selector is authoritative. There are {len(new_words)} new words and
{len(review_words)} review words in this task. Use exactly those words and no
others. If the new-word list is empty, create a review-only task; never invent
additional new words from memory.

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
- Use exactly the provided word counts; do not add, remove, or substitute words.
- Set is_review to true only for words from the provided Review words list.
- matching must contain 10 items.
- fill_blank must contain 10 items.
- keyword_reading must contain 3 short math/science reading questions.
- Keep examples concise.
- If a provided Chinese or definition field is blank, fill it with a concise accurate value.
- Prefer math/science/academic meaning when a word has multiple meanings.{personal_section}"""

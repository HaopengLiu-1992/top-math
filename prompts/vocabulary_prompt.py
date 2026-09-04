import json


def system_prompt() -> str:
    return """You generate Grade 5-8 academic vocabulary practice.
Output ONLY valid JSON. No markdown, no explanation.
Use clear grade-level English suitable for an English learner.
Prioritize precise academic meanings, morphology, collocations, and productive use.
Difficulty means useful academic transfer, not rare or obscure words."""


def user_prompt(date_str: str, grade_level: int, new_words: list[dict], review_words: list[dict],
                personal_prompt: str = "", quality_feedback: str = "") -> str:
    personal_section = ""
    if personal_prompt.strip():
        personal_section = f"""

Personal prompt from the learner or parent:
{personal_prompt.strip()}
Treat this as a learner preference and follow it when compatible with the
grade level, vocabulary task structure, and required output format.
"""

    retry_section = ""
    if quality_feedback:
        retry_section = f"""

The previous response failed these checks:
{quality_feedback}
Correct every issue in the new response.
"""

    total_words = len(new_words) + len(review_words)
    return f"""Generate today's academic vocabulary task.

Date: {date_str}
Grade level: {grade_level}
New words:
{json.dumps(new_words, indent=2, ensure_ascii=False)}

Review words:
{json.dumps(review_words, indent=2, ensure_ascii=False)}

The local selector is authoritative. There are {len(new_words)} new words and
{len(review_words)} spaced-review words in this task. Use exactly those words and no
others. If the new-word list is empty, create a review-only task; never invent
additional new words from memory.
{retry_section}

Return EXACTLY this JSON shape:
{{
  "date": "{date_str}",
  "subject": "english",
  "task_type": "vocabulary",
  "grade_level": {grade_level},
  "title": "Grade-Level Academic Vocabulary",
  "estimated_minutes": 25,
  "words": [
    {{
      "id": "v_001",
      "word": "quotient",
      "category": "math_operations",
      "chinese": "商",
      "definition": "the answer to a division problem",
      "morphology": "quotient",
      "collocation": "calculate the quotient",
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
- matching must contain {total_words} items and practice every selected word exactly once.
- fill_blank must contain {total_words} items and practice every selected word exactly once.
- keyword_reading must contain 3 short academic, history, math, or science reading questions.
- Every keyword_reading entry must be a genuine question ending in a question mark.
- Give each word an accurate academic definition, useful morphology or word family,
  a natural collocation, and a concise grade-level example.
- Quick checks must test the stated meaning and have one unambiguous answer.
- Keep one coherent topic cluster when the selected words share a topic_group.
- If a provided Chinese or definition field is blank, fill it with a concise accurate value.
- Correct an inaccurate supplied dictionary definition to the intended academic meaning.
- Prefer math/science/academic meaning when a word has multiple meanings.{personal_section}"""

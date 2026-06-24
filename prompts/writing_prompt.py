def system_prompt() -> str:
    return """You generate short grade-level English writing practice for an English learner.
Output ONLY valid JSON. No markdown.
Use clear sentences that a student can memorize and reuse in school writing."""


def user_prompt(date_str: str, grade_level: int, focus: str) -> str:
    return f"""Generate today's English writing memorization task.

Date: {date_str}
Grade level: {grade_level}
Focus: {focus}

Return EXACTLY this JSON shape:
{{
  "date": "{date_str}",
  "subject": "english",
  "task_type": "writing",
  "grade_level": {grade_level},
  "title": "Opinion Writing Memory Set",
  "estimated_minutes": 20,
  "opinion": {{
    "claim": "Reading every day helps students become stronger learners.",
    "chinese": "每天阅读能帮助学生成为更强的学习者。",
    "sentence_frame": "I believe ___ because ___.",
    "memorize_line": "I believe reading every day helps students become stronger learners."
  }},
  "examples": [
    {{
      "id": "example_001",
      "type": "personal",
      "example": "For example, when I read a science article, I learn new words and facts.",
      "chinese": "例如，当我读一篇科学文章时，我会学到新单词和新事实。",
      "why_it_works": "This example connects reading to vocabulary and knowledge.",
      "memorize_line": "For example, reading science articles can teach me new words and facts.",
      "fill_blank": "For example, reading science articles can teach me new ___ and ___.",
      "answer": "words; facts"
    }}
  ],
  "mini_outline": [
    "Opinion: ...",
    "Example 1: ...",
    "Example 2: ...",
    "Example 3: ...",
    "Closing: ..."
  ],
  "practice": {{
    "recitation_check": [
      {{"id": "opinion", "prompt": "Say the opinion sentence from memory.", "answer": "..."}},
      {{"id": "example_001", "prompt": "Say example 1 from memory.", "answer": "..."}}
    ],
    "rewrite_task": "Write one short paragraph using the opinion and two examples."
  }}
}}

Rules:
- Generate exactly 1 opinion/claim and exactly 3 examples.
- Each memorize_line must be one sentence and easy to recite.
- Examples should be school-friendly and useful for opinion or short-response writing.
- At least one example should connect to math, science, or academic learning.
- Chinese translations must directly translate the exact English opinion/example sentence; do not add extra details.
- Keep the full task suitable for 15-20 minutes."""

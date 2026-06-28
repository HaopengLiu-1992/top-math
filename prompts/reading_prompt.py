import json


def system_prompt() -> str:
    return """You generate grade-level reading practice for an English learner.
Output ONLY valid JSON. No markdown.
Use clear, age-appropriate English. Questions must have unambiguous answers."""


def user_prompt(date_str: str, grade_level: int, subject: str, focus: str,
                guardrail: dict | None = None) -> str:
    if subject == "science":
        passage_kind = "science nonfiction passage about life science, earth science, physical science, or scientific investigation"
        task_type = "science_reading"
    else:
        passage_kind = "English reading passage with school-friendly fiction or nonfiction"
        task_type = "english_reading"

    guardrail_text = ""
    if guardrail:
        guardrail_text = f"""
Reading guardrail:
{json.dumps(guardrail, indent=2, ensure_ascii=False)}

Use the slot and core_concept as the content target. Do not write about the
avoid_concepts except as clearly different background references.
Include the external_passage_id in metadata.reading_guardrail.external_passage_id.
"""

    return f"""Generate a daily {subject} reading task.

Date: {date_str}
Grade level: {grade_level}
Focus: {focus}
Passage kind: {passage_kind}
{guardrail_text}

Return EXACTLY this JSON shape:
{{
  "date": "{date_str}",
  "subject": "{subject}",
  "task_type": "reading",
  "grade_level": {grade_level},
  "title": "Reading Practice",
  "estimated_minutes": 25,
  "passage": {{
    "title": "Passage title",
    "genre": "nonfiction",
    "word_count": 500,
    "text": "Full passage text..."
  }},
  "vocabulary": [
    {{"word": "evidence", "definition": "information that supports an idea", "chinese": "证据", "sentence": "Evidence helps scientists support a claim."}}
  ],
  "questions": [
    {{"id": "q_001", "type": "main_idea", "skill": "main idea", "question": "...", "answer": "..."}},
    {{"id": "q_002", "type": "detail", "skill": "text evidence", "question": "...", "answer": "..."}},
    {{"id": "q_003", "type": "inference", "skill": "inference", "question": "...", "answer": "..."}},
    {{"id": "q_004", "type": "vocabulary_context", "skill": "vocabulary in context", "question": "...", "answer": "..."}},
    {{"id": "q_005", "type": "short_response", "skill": "written response", "question": "...", "answer": "..."}}
  ],
  "metadata": {{
    "focus": "{focus}",
    "task_template": "{task_type}",
    "reading_guardrail": {{}}
  }}
}}

Rules:
- Passage length should be 450-650 words for grades 5-6 and 650-850 words for grades 7-8.
- Include 8 vocabulary words.
- Include 8 questions total: main idea, details, inference, vocabulary in context, author's purpose or claim/evidence, and short response.
- For science, include at least one question about evidence, cause/effect, data, or scientific explanation.
- The passage must stay on the selected core_concept and avoid repeating prior concepts.
- Answers must be concise and correct."""

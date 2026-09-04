import json


def system_prompt() -> str:
    return """You generate grade-level reading practice for an English learner.
Output ONLY valid JSON. No markdown.
Keep content at the requested grade level while making language clear.
Questions must have unambiguous, passage-grounded answers. Never invent a
quotation, date, scientific result, or historical source."""


def user_prompt(date_str: str, grade_level: int, subject: str, focus: str,
                guardrail: dict | None = None) -> str:
    if subject == "science":
        passage_kind = "standards-aligned science reading based on the supplied grade-level curriculum slot"
        task_type = "science_reading"
        subject_rules = """Build around a real phenomenon, model, investigation, or small data set.
Explain the required scientific content, not merely a fun fact. Include questions
about mechanism, evidence/data, cause and effect, and applying the concept."""
    else:
        passage_kind = "History + English Reading based on the supplied grade-level history curriculum slot"
        task_type = "english_reading"
        subject_rules = """Teach the specified history content while practicing English reading.
Include chronology or cause/effect, historical context, comparison or perspective,
and text evidence. If using a source excerpt, identify it accurately; otherwise
paraphrase and do not put invented words inside quotation marks."""

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
Subject-specific rules:
{subject_rules}
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
    "text": "Full passage text...",
    "curriculum_standard": "The exact standard from the selected slot",
    "source_note": "Brief note naming any historical source or data used; empty if none"
  }},
  "vocabulary": [
    {{"word": "evidence", "definition": "information that supports an idea", "chinese": "证据", "sentence": "Evidence helps scientists support a claim."}}
  ],
  "questions": [
    {{"id": "q_001", "type": "main_idea", "skill": "main idea", "question": "...", "answer": "..."}},
    {{"id": "q_002", "type": "detail", "skill": "text evidence", "question": "...", "answer": "..."}},
    {{"id": "q_003", "type": "inference", "skill": "inference", "question": "...", "answer": "..."}},
    {{"id": "q_004", "type": "vocabulary_context", "skill": "vocabulary in context", "target_word": "a vocabulary word used exactly in the passage", "question": "...", "answer": "..."}},
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
- Every vocabulary word must appear in the passage in the exact displayed form.
- Include 8 questions total. Use exactly one vocabulary_context question with a
  target_word that appears exactly in the passage.
- At least four questions must require Grade 6-8 DOK 2-3 thinking, such as
  cause/effect, comparison, inference, data interpretation, source analysis,
  or explaining how evidence supports an answer.
- Include one short response that requires two passage details and an explanation.
- For science, include questions about evidence/data, mechanism or cause/effect,
  and application of the scientific idea.
- For history, include questions about chronology or cause/effect, context or
  perspective, and historical evidence.
- Cover every required_content item from the selected curriculum slot accurately.
- Put the selected slot.standard into passage.curriculum_standard unchanged.
- The passage must stay on the selected core_concept and avoid repeating prior concepts.
- Answers must be concise, correct, and directly supported by the passage."""

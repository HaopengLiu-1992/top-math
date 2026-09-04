import json


def system_prompt() -> str:
    return """You generate short grade-level English writing practice for an English learner.
Output ONLY valid JSON. No markdown.
The goal is writing a short three-paragraph essay, not memorizing a finished essay.
Use clear, grade-appropriate language and teach the student to Answer, give
Evidence, and Explain."""


def user_prompt(date_str: str, grade_level: int, focus: str,
                plan: list[dict] | None = None, history: dict | None = None,
                feedback: str = "", writing_mode: str = "opinion",
                focus_words: list[dict] | None = None,
                source_context: dict | None = None) -> str:
    plan = plan or [
        {"position": 1, "type": "personal_experience"},
        {"position": 2, "type": "math_science_application"},
        {"position": 3, "type": "reading_evidence"},
    ]
    history = history or {}
    focus_words = focus_words or []
    source_context = source_context or {}
    mode_labels = {
        "summary": "Summary",
        "opinion": "Opinion / Argument",
        "text_based_response": "Text-Based Response",
    }
    mode_label = mode_labels.get(writing_mode, "Opinion / Argument")
    source_instruction = ""
    if writing_mode in {"summary", "text_based_response"}:
        if source_context.get("text"):
            source_instruction = f"""

Use this existing reading passage as the source. Keep it unchanged:
{json.dumps(source_context, indent=2, ensure_ascii=False)}
"""
        else:
            source_instruction = """

Create a short informational source passage of 180-250 words for the student
to read. It must be self-contained and suitable for the requested grade.
"""
    focus_word_instruction = json.dumps(focus_words, indent=2, ensure_ascii=False)
    guardrail_feedback = ""
    if feedback:
        guardrail_feedback = f"""

The previous draft failed this quality check:
{feedback}
Generate a genuinely different draft and follow every rule below.
"""

    return f"""Generate today's English writing practice task.

Date: {date_str}
Grade level: {grade_level}
Focus: {focus}
Writing mode: {writing_mode} ({mode_label})

This is the small vocabulary set to apply in writing. Use exactly these five
words and do not replace them:
{focus_word_instruction}
{source_instruction}

Anti-repetition guardrail:
Use these exact example types in this exact order:
{json.dumps(plan, indent=2, ensure_ascii=False)}

Do not reuse or closely paraphrase these recent opinion sentences:
{json.dumps(history.get("avoid_opinions", []), indent=2, ensure_ascii=False)}

Do not reuse or closely paraphrase these recent example sentences:
{json.dumps(history.get("avoid_examples", []), indent=2, ensure_ascii=False)}

Do not reuse these recent example-starter signatures:
{json.dumps(history.get("avoid_starters", []), indent=2, ensure_ascii=False)}
{guardrail_feedback}

Return EXACTLY this JSON shape:
{{
  "date": "{date_str}",
  "subject": "english",
  "task_type": "writing",
  "grade_level": {grade_level},
  "title": "Daily Writing Lab — {mode_label}",
  "estimated_minutes": 20,
  "writing_mode": "{writing_mode}",
  "mode_label": "{mode_label}",
  "time_plan": [
    {{"minutes": 5, "activity": "Use each focus word in an original sentence."}},
    {{"minutes": 10, "activity": "Write a three-paragraph, 8-12 sentence first draft."}},
    {{"minutes": 5, "activity": "Revise one sentence and complete the checklist."}}
  ],
  "source": {{
    "title": "A short source title",
    "text": "A source passage for summary or text-based response; use an empty string for opinion mode."
  }},
  "writing_prompt": "Write a short essay in three paragraphs and 8-12 sentences.",
  "paragraph_plan": [
    {{"label": "Introduction", "purpose": "Answer the prompt and state the main idea."}},
    {{"label": "Body", "purpose": "Give evidence or a specific example and explain it."}},
    {{"label": "Conclusion", "purpose": "Restate the main idea and close the essay."}}
  ],
  "structure": [
    {{"label": "Answer", "instruction": "Answer the prompt directly.", "frame": "I think ___ because ___."}},
    {{"label": "Evidence", "instruction": "Give a detail, example, or reason.", "frame": "For example, ___."}},
    {{"label": "Explain", "instruction": "Explain how the evidence supports your answer.", "frame": "This shows that ___."}}
  ],
  "focus_words": [
    {{"word": "evidence", "meaning": "information that supports an idea", "chinese": "证据"}},
    {{"word": "reason", "meaning": "a cause or explanation", "chinese": "理由"}},
    {{"word": "explain", "meaning": "to make an idea clear", "chinese": "解释"}},
    {{"word": "result", "meaning": "what happens because of something", "chinese": "结果"}},
    {{"word": "support", "meaning": "to provide evidence for an idea", "chinese": "支持"}}
  ],
  "opinion": {{
    "claim": "Reading every day helps students become stronger learners.",
    "chinese": "每天阅读能帮助学生成为更强的学习者。",
    "sentence_frame": "I believe ___ because ___.",
    "memorize_line": "I believe reading every day helps students become stronger learners."
  }},
  "examples": [
    {{
      "id": "example_001",
      "type": "personal_experience",
      "reference_sentence": "For example, reading science articles can teach me new words and facts.",
      "why_it_works": "This is a model for adding a specific example."
    }}
  ],
  "practice": {{
    "word_sentences": [
      {{"word": "evidence", "prompt": "Use evidence in one sentence about today's topic.", "model": "Evidence supports a clear answer."}},
      {{"word": "reason", "prompt": "Use reason in one sentence about today's topic.", "model": "One reason is that practice builds confidence."}},
      {{"word": "explain", "prompt": "Use explain in one sentence about today's topic.", "model": "I can explain my answer with a detail."}},
      {{"word": "result", "prompt": "Use result in one sentence about today's topic.", "model": "The result shows what happened after the experiment."}},
      {{"word": "support", "prompt": "Use support in one sentence about today's topic.", "model": "Details support the writer's main idea."}}
    ],
    "draft_task": "Write a short essay in three paragraphs and 8-12 sentences using Answer → Evidence → Explain.",
    "revision_task": "Revise the essay by improving one sentence, adding a detail, checking the five focus words, and confirming the three paragraphs are clear.",
    "checklist": [
      "I answered the prompt directly.",
      "I included evidence or a specific detail.",
      "I explained how the evidence supports my answer.",
      "I used all five focus words correctly.",
      "I used an introduction, body, and conclusion paragraph.",
      "I checked capitals, punctuation, and complete sentences."
    ],
    "sample_response": "A short 8-12 sentence, three-paragraph model response that demonstrates the structure."
  }}
}}

Rules:
- Generate exactly 1 prompt and one source object. For opinion mode, source.text may be empty.
- For summary mode, ask the student to state the main idea and two key details without adding an opinion.
- For text_based_response mode, require at least two details from the source and an explanation of each.
- For opinion mode, require a clear answer, one reason or example, and an explanation.
- The student target response must be an 8-12 sentence, three-paragraph short essay and fit a 15-20 minute session.
- Use a simple 5 + 10 + 5 minute plan: word application, first draft, revision.
- Return exactly five focus_words matching the provided words, and exactly five word_sentences in the same order.
- Each word_sentence must ask the student to use that focus word in an original sentence and include a short model.
- Include an 8-12 sentence, three-paragraph sample_response for the answer key; it must model the structure without sounding like an instruction to copy.
- Generate exactly 1 opinion/claim and exactly 3 reference examples.
- Set the three example type fields to the exact planned types, in order.
- Each reference sentence must be one school-friendly sentence that demonstrates a useful move; it is a model, not a memorization requirement.
- The math_science_application example must connect to math or science.
- Use three different sentence starters. Do not begin every example with "For example".
- Keep the full task suitable for 15-20 minutes."""

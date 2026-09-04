import json


TARGET_WORDS = 50
MIN_WORDS = 45
MAX_WORDS = 65


def system_prompt() -> str:
    return """You generate focused grade-level English writing practice for an English learner.
Output ONLY valid JSON. No markdown.
The student writes one short paragraph of about 50 words. Teach the student to
Answer or Claim, give Evidence, and Explain. Do not turn vocabulary memorization
into part of this writing task."""


def user_prompt(date_str: str, grade_level: int, focus: str,
                history: dict | None = None, feedback: str = "",
                writing_mode: str = "opinion",
                source_context: dict | None = None) -> str:
    history = history or {}
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

Use this existing History + English Reading passage as the source. Keep its
facts unchanged and make the writing prompt answerable from it:
{json.dumps(source_context, indent=2, ensure_ascii=False)}
"""
        else:
            source_instruction = """

Create a self-contained 180-250 word history source passage appropriate for
the requested grade. Use established historical facts and avoid disputed or
overly simplified claims.
"""

    retry_instruction = ""
    if feedback:
        retry_instruction = f"""

The previous draft failed these checks:
{feedback}
Correct every issue while keeping the same required JSON shape.
"""

    mode_rules = {
        "summary": (
            "Ask for the main idea and two important details. The student must not "
            "add an opinion. Map Answer to Main Idea, Evidence to Key Details, and "
            "Explain to how the details connect to the main idea."
        ),
        "opinion": (
            "Ask a grade-appropriate question with more than one defensible answer. "
            "Require one clear claim, one specific reason or example, and an explanation."
        ),
        "text_based_response": (
            "Ask an analytical question about the source. Require a direct answer, "
            "at least two accurate source details, and an explanation of how they support the answer."
        ),
    }[writing_mode]

    return f"""Generate today's English writing practice task.

Date: {date_str}
Grade level: {grade_level}
Focus: {focus}
Writing mode: {writing_mode} ({mode_label})
Target: one paragraph, {MIN_WORDS}-{MAX_WORDS} words, normally 5-7 sentences.
{source_instruction}

Mode-specific rule:
{mode_rules}

Do not reuse or closely paraphrase these recent prompts:
{json.dumps(history.get("avoid_prompts", []), indent=2, ensure_ascii=False)}

Do not reuse or closely paraphrase these recent sample responses:
{json.dumps(history.get("avoid_samples", []), indent=2, ensure_ascii=False)}
{retry_instruction}

Return EXACTLY this JSON shape:
{{
  "date": "{date_str}",
  "subject": "english",
  "task_type": "writing",
  "task_version": 2,
  "grade_level": {grade_level},
  "title": "Daily 50-Word Writing — {mode_label}",
  "estimated_minutes": 20,
  "writing_mode": "{writing_mode}",
  "mode_label": "{mode_label}",
  "target_words": {TARGET_WORDS},
  "target_range": [{MIN_WORDS}, {MAX_WORDS}],
  "time_plan": [
    {{"minutes": 3, "activity": "Read the prompt and plan Answer/Claim, Evidence, and Explain."}},
    {{"minutes": 10, "activity": "Write one paragraph of about 50 words."}},
    {{"minutes": 7, "activity": "Use feedback to revise structure first, then one language skill."}}
  ],
  "source": {{
    "title": "A short source title",
    "text": "Use the supplied source for reading-based modes; use an empty string for opinion mode."
  }},
  "writing_prompt": "One clear question that leads to a focused 50-word paragraph.",
  "structure": [
    {{"label": "Answer / Claim", "instruction": "Answer directly in one sentence.", "frame": "The main idea is ___ because ___."}},
    {{"label": "Evidence", "instruction": "Add one or two accurate details.", "frame": "One important detail is ___."}},
    {{"label": "Explain", "instruction": "Explain how the evidence supports the answer.", "frame": "This shows that ___."}}
  ],
  "practice": {{
    "draft_task": "Write one 45-65 word paragraph, normally 5-7 sentences.",
    "revision_rounds": [
      {{"round": 1, "focus": "structure_and_evidence", "instruction": "Check only the answer/claim, evidence, and explanation."}},
      {{"round": 2, "focus": "one_language_skill", "instruction": "After revising ideas, correct only one recurring language category."}}
    ],
    "checklist": [
      "I answered the prompt directly.",
      "I included accurate evidence or a specific detail.",
      "I explained how the evidence supports my answer.",
      "I wrote one paragraph of about 50 words.",
      "I checked capitals, punctuation, and complete sentences."
    ],
    "sample_response": "A 45-65 word one-paragraph model that follows the mode-specific rule."
  }}
}}

Rules:
- Generate exactly one prompt and one source object.
- Never require the student to use the daily vocabulary words.
- Keep the task to one paragraph. Do not request an introduction, body, and conclusion.
- The student target is {MIN_WORDS}-{MAX_WORDS} words and normally 5-7 complete sentences.
- The sample response must also be {MIN_WORDS}-{MAX_WORDS} words in one paragraph.
- Sentence frames are optional scaffolds, not text to memorize or copy.
- For opinion mode, source.text must be empty.
- Keep the full task suitable for 15-20 minutes."""


def review_system_prompt() -> str:
    return """You are a careful writing coach for a grade-level English learner.
Output ONLY valid JSON. No markdown. Respond to the student's actual draft.
Preserve the student's ideas and voice. Never rewrite the entire paragraph."""


def review_user_prompt(task: dict, draft: str, review_round: int) -> str:
    source = task.get("source") or {}
    shared = f"""Writing mode: {task.get('writing_mode', 'opinion')}
Grade level: {task.get('grade_level', 6)}
Prompt: {task.get('writing_prompt', '')}
Source: {json.dumps(source, ensure_ascii=False)}
Student draft ({len(draft.split())} words):
{draft}
"""
    if review_round == 1:
        return shared + """

Review ONLY content organization and evidence. Do not correct grammar, spelling,
punctuation, or word choice in this round. Judge evidence against the source
when a source is provided.

Return exactly:
{
  "round": 1,
  "focus": "structure_and_evidence",
  "strength": "one specific thing the student did well",
  "answer_feedback": "one concise note about the direct answer or claim",
  "evidence_feedback": "one concise note about evidence and explanation",
  "next_step": "one concrete revision action",
  "ready_for_round_2": true
}"""

    return shared + """

The student has already revised content. Review ONLY ONE recurring language
category. Choose the highest-impact category from sentence completeness,
verb tense/agreement, articles, punctuation/capitalization, or word choice.
Give at most two corrections. Do not add new ideas or rewrite the paragraph.

Return exactly:
{
  "round": 2,
  "focus": "one_language_skill",
  "language_category": "one category only",
  "strength": "one specific language success",
  "corrections": [
    {"original": "exact short excerpt", "revision": "corrected excerpt", "why": "brief explanation"}
  ],
  "next_step": "one concrete proofreading action"
}"""

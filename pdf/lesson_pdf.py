from html import escape

from reportlab.platypus import Paragraph, Spacer


def append_lesson(story: list, lesson: dict | None, section_style,
                  paragraph_style, step_style=None):
    if not lesson:
        return

    story.append(Paragraph("Lesson", section_style))
    title = lesson.get("title")
    if title:
        story.append(Paragraph(f"<b>{escape(title)}</b>", paragraph_style))

    plain_text = lesson.get("plain_text")
    if plain_text:
        _append_plain_text(story, plain_text, paragraph_style)
        story.append(Spacer(1, 6))
        return

    objective = lesson.get("objective")
    if objective:
        story.append(Paragraph(f"Objective: {escape(objective)}", paragraph_style))
    explanation = lesson.get("concept_explanation")
    if explanation:
        story.append(Paragraph(escape(explanation), paragraph_style))

    for example in lesson.get("worked_examples", []):
        story.append(Paragraph(escape(example.get("problem", "Example")), paragraph_style))
        for step in example.get("steps", []):
            style = step_style or paragraph_style
            story.append(Paragraph(f"      {escape(step)}", style))
        note = example.get("teaching_note")
        if note:
            story.append(Paragraph(f"Note: {escape(note)}", paragraph_style))

    mistakes = lesson.get("common_mistakes", [])
    if mistakes:
        story.append(Paragraph("<b>Common mistakes</b>", paragraph_style))
        for item in mistakes:
            mistake = item.get("mistake", "")
            fix = item.get("fix", "")
            story.append(Paragraph(f"- {escape(mistake)} Fix: {escape(fix)}", paragraph_style))

    checks = lesson.get("try_this_first", [])
    if checks:
        story.append(Paragraph("<b>Try this first</b>", paragraph_style))
        for prompt in checks:
            story.append(Paragraph(f"- {escape(prompt)}", paragraph_style))
    story.append(Spacer(1, 6))


def _append_plain_text(story: list, plain_text: str, paragraph_style):
    for block in plain_text.split("\n\n"):
        text = block.strip()
        if not text:
            continue
        lines = [escape(line.strip()) for line in text.splitlines()]
        story.append(Paragraph("<br/>".join(lines), paragraph_style))

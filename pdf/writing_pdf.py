from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from pdf.fonts import paragraph_text
from storage import writing_store


def build_writing(task: dict) -> Path:
    filename = _path(task, "writing.pdf")
    story, styles = _base_story(task, task.get("title", "Daily Writing Lab"))
    section = styles["section"]
    normal = styles["normal"]
    highlight = styles["highlight"]

    source = task.get("source") or {}
    if source.get("text"):
        story.append(Paragraph("Read First", section))
        story.append(Paragraph(f"<b>{paragraph_text(source.get('title', 'Source passage'))}</b>", normal))
        story.append(Paragraph(paragraph_text(source["text"]), normal))

    story.append(Paragraph("Writing Prompt", section))
    story.append(Paragraph(paragraph_text(task.get("writing_prompt", "Write one short paragraph.")), highlight))

    paragraph_plan = task.get("paragraph_plan") or []
    if paragraph_plan:
        story.append(Paragraph("Short Essay Plan", section))
        for item in paragraph_plan:
            story.append(Paragraph(
                f"<b>{paragraph_text(item.get('label', 'Paragraph'))}</b>: "
                f"{paragraph_text(item.get('purpose', ''))}",
                normal,
            ))

    structure = task.get("structure") or []
    if structure:
        story.append(Paragraph("Answer → Evidence → Explain", section))
        for item in structure:
            story.append(Paragraph(
                f"<b>{paragraph_text(item.get('label', 'Step'))}</b>: "
                f"{paragraph_text(item.get('instruction', ''))}<br/>"
                f"Frame: {paragraph_text(item.get('frame', ''))}",
                normal,
            ))

    focus_words = task.get("focus_words") or []
    if focus_words:
        story.append(Paragraph("Focus Words — Write Your Own Sentences", section))
        for item in focus_words:
            story.append(Paragraph(
                f"<b>{paragraph_text(item.get('word', ''))}</b> "
                f"({paragraph_text(item.get('chinese', ''))}) — "
                f"{paragraph_text(item.get('meaning', ''))}<br/>"
                "Your sentence: ____________________________________________________",
                normal,
            ))

    practice = task.get("practice", {})
    story.append(Paragraph("Draft and Revision", section))
    story.append(Paragraph(paragraph_text(practice.get("draft_task", "Write one paragraph of about 50 words.")), normal))
    story.append(Paragraph("First draft:", normal))
    line_count = 6 if task.get("task_version") == 2 else 9
    for _ in range(line_count):
        story.append(Paragraph("__________________________________________________________________", normal))
    rounds = practice.get("revision_rounds") or []
    for item in rounds:
        story.append(Paragraph(
            f"<b>Round {item.get('round', '')}</b>: {paragraph_text(item.get('instruction', ''))}",
            normal,
        ))
    story.append(Paragraph(paragraph_text(practice.get("revision_task", "Revise the same paragraph.")), normal))
    story.append(Paragraph("Revised draft:", normal))
    for _ in range(line_count):
        story.append(Paragraph("__________________________________________________________________", normal))

    if task.get("examples"):
        story.append(Paragraph("Reference Sentences — Do Not Memorize", section))
        for idx, item in enumerate(task.get("examples", []), 1):
            sentence = item.get("reference_sentence") or item.get("memorize_line") or item.get("example", "")
            story.append(Paragraph(f"{idx}. {paragraph_text(sentence)}", normal))

    _build_doc(filename, story)
    return filename


def build_answers(task: dict) -> Path:
    filename = _path(task, "answers.pdf")
    story, styles = _base_story(task, "Writing Reference")
    section = styles["section"]
    normal = styles["normal"]
    answer = styles["answer"]

    practice = task.get("practice", {})
    word_sentences = practice.get("word_sentences") or []
    if word_sentences:
        story.append(Paragraph("Focus Word Sentence Models", section))
        for item in word_sentences:
            story.append(Paragraph(paragraph_text(item.get("prompt", "")), normal))
            story.append(Paragraph(f"Model: {paragraph_text(item.get('model', ''))}", answer))

    if practice.get("sample_response"):
        story.append(Paragraph("Reference Response", section))
        story.append(Paragraph(paragraph_text(practice["sample_response"]), answer))

    if practice.get("recitation_check"):
        story.append(Paragraph("Legacy Recitation Check", section))
        for item in practice["recitation_check"]:
            story.append(Paragraph(paragraph_text(item.get("prompt", "")), normal))
            story.append(Paragraph(f"Answer: {paragraph_text(item.get('answer', ''))}", answer))

    legacy_fill_blanks = [item for item in task.get("examples", []) if item.get("fill_blank")]
    if legacy_fill_blanks:
        story.append(Paragraph("Legacy Fill-in Practice", section))
        for idx, item in enumerate(legacy_fill_blanks, 1):
            story.append(Paragraph(f"{idx}. {paragraph_text(item.get('fill_blank', ''))}", normal))
            story.append(Paragraph(f"Answer: {paragraph_text(item.get('answer', ''))}", answer))

    _build_doc(filename, story)
    return filename


def _path(task: dict, name: str) -> Path:
    out = writing_store.pdf_dir(task["date"])
    out.mkdir(parents=True, exist_ok=True)
    return out / name


def _base_story(task: dict, title: str):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=16, spaceAfter=4)
    subtitle_style = ParagraphStyle("subtitle", parent=styles["Normal"], fontSize=10,
                                    textColor=colors.grey, spaceAfter=12)
    section_style = ParagraphStyle("section", parent=styles["Heading2"], fontSize=12,
                                   spaceBefore=14, spaceAfter=6)
    normal_style = ParagraphStyle("writing_normal", parent=styles["Normal"], fontSize=10,
                                  spaceAfter=8, leading=14)
    highlight_style = ParagraphStyle("highlight", parent=styles["Normal"], fontSize=11,
                                     textColor=colors.HexColor("#1f3f7a"),
                                     spaceAfter=8, leading=15)
    answer_style = ParagraphStyle("answer", parent=styles["Normal"], fontSize=10,
                                  textColor=colors.HexColor("#1a6b1a"), spaceAfter=5, leading=13)
    story = [
        Paragraph(title, title_style),
        Paragraph(paragraph_text(f"{task['date']} | Grade {task.get('grade_level', '-')}"), subtitle_style),
        HRFlowable(width="100%", thickness=0.5, color=colors.black),
        Spacer(1, 8),
    ]
    return story, {
        "section": section_style,
        "normal": normal_style,
        "highlight": highlight_style,
        "answer": answer_style,
    }


def _build_doc(filename: Path, story: list):
    doc = SimpleDocTemplate(str(filename), pagesize=letter,
                            rightMargin=0.75 * inch, leftMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    doc.build(story)

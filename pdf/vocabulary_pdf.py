from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from storage import vocabulary_store


def build_vocabulary(task: dict) -> Path:
    filename = _path(task, "vocabulary.pdf")
    story, styles = _base_story(task, "Vocabulary Practice")
    section = styles["section"]
    normal = styles["normal"]

    story.append(Paragraph("Words", section))
    for idx, item in enumerate(task.get("words", []), 1):
        label = "Review" if item.get("is_review") else "New"
        story.append(Paragraph(
            f"{idx}. <b>{item['word']}</b> ({label}) - {item.get('chinese', '')}<br/>"
            f"{item.get('definition', '')}<br/><i>{item.get('example', '')}</i>",
            normal,
        ))

    practice = task.get("practice", {})
    story.append(Paragraph("Matching", section))
    for item in practice.get("matching", []):
        story.append(Paragraph(f"- {item.get('word', '')}: ____________________", normal))

    story.append(Paragraph("Fill in the Blank", section))
    for item in practice.get("fill_blank", []):
        story.append(Paragraph(f"- {item.get('sentence', '')}", normal))

    story.append(Paragraph("Reading Bridge", section))
    for idx, item in enumerate(practice.get("keyword_reading", []), 1):
        story.append(Paragraph(f"{idx}. {item.get('question', '')}", normal))
        story.append(Paragraph("Keyword: ____________________", normal))

    _build_doc(filename, story)
    return filename


def build_answers(task: dict) -> Path:
    filename = _path(task, "answers.pdf")
    story, styles = _base_story(task, "Vocabulary Answer Key")
    section = styles["section"]
    normal = styles["normal"]
    answer = styles["answer"]

    story.append(Paragraph("Quick Checks", section))
    for idx, item in enumerate(task.get("words", []), 1):
        story.append(Paragraph(f"{idx}. {item.get('quick_check', '')}", normal))
        story.append(Paragraph(f"Answer: {item.get('answer', '')}", answer))

    practice = task.get("practice", {})
    story.append(Paragraph("Matching", section))
    for item in practice.get("matching", []):
        story.append(Paragraph(f"{item.get('word', '')}: {item.get('definition', '')}", answer))

    story.append(Paragraph("Fill in the Blank", section))
    for item in practice.get("fill_blank", []):
        story.append(Paragraph(f"{item.get('sentence', '')}", normal))
        story.append(Paragraph(f"Answer: {item.get('answer', '')}", answer))

    story.append(Paragraph("Reading Bridge", section))
    for item in practice.get("keyword_reading", []):
        story.append(Paragraph(f"{item.get('question', '')}", normal))
        story.append(Paragraph(
            f"Keyword: {item.get('keyword', '')} - {item.get('meaning', '')}",
            answer,
        ))

    _build_doc(filename, story)
    return filename


def _path(task: dict, name: str) -> Path:
    out = vocabulary_store.pdf_dir(task["date"])
    out.mkdir(parents=True, exist_ok=True)
    return out / name


def _base_story(task: dict, title: str):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=16, spaceAfter=4)
    subtitle_style = ParagraphStyle("subtitle", parent=styles["Normal"], fontSize=10,
                                    textColor=colors.grey, spaceAfter=12)
    section_style = ParagraphStyle("section", parent=styles["Heading2"], fontSize=12,
                                   spaceBefore=14, spaceAfter=6)
    normal_style = ParagraphStyle("vocab_normal", parent=styles["Normal"], fontSize=10,
                                  spaceAfter=8, leading=14)
    answer_style = ParagraphStyle("answer", parent=styles["Normal"], fontSize=10,
                                  textColor=colors.HexColor("#1a6b1a"), spaceAfter=5, leading=13)
    custom = {
        "section": section_style,
        "normal": normal_style,
        "answer": answer_style,
    }
    story = [
        Paragraph(title, title_style),
        Paragraph(f"{task['date']} | Grade {task.get('grade_level', '-')}", subtitle_style),
        HRFlowable(width="100%", thickness=0.5, color=colors.black),
        Spacer(1, 8),
    ]
    return story, custom


def _build_doc(filename: Path, story: list):
    doc = SimpleDocTemplate(str(filename), pagesize=letter,
                            rightMargin=0.75 * inch, leftMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    doc.build(story)

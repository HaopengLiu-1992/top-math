from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from domain.daily_task import TaskScope
from pdf.fonts import register_cjk_font
from storage import reading_store


def build_reading(scope: TaskScope, task: dict) -> Path:
    filename = _path(scope, task, "reading.pdf")
    story, styles = _base_story(task, "Reading Practice")
    section = styles["section"]
    normal = styles["normal"]

    passage = task.get("passage", {})
    story.append(Paragraph(passage.get("title", "Passage"), section))
    story.append(Paragraph(passage.get("text", ""), normal))

    story.append(Paragraph("Vocabulary", section))
    for item in task.get("vocabulary", []):
        story.append(Paragraph(
            f"<b>{item.get('word', '')}</b> - {item.get('definition', '')}",
            normal,
        ))

    story.append(Paragraph("Questions", section))
    for idx, item in enumerate(task.get("questions", []), 1):
        story.append(Paragraph(f"{idx}. {item.get('question', '')}", normal))
        story.append(Spacer(1, 8))

    _build_doc(filename, story)
    return filename


def build_answers(scope: TaskScope, task: dict) -> Path:
    filename = _path(scope, task, "answers.pdf")
    story, styles = _base_story(task, "Reading Answer Key")
    section = styles["section"]
    normal = styles["normal"]
    answer = styles["answer"]

    story.append(Paragraph("Vocabulary", section))
    for item in task.get("vocabulary", []):
        story.append(Paragraph(
            f"<b>{item.get('word', '')}</b> ({item.get('chinese', '')}) - {item.get('definition', '')}<br/>"
            f"<i>{item.get('sentence', '')}</i>",
            normal,
        ))

    story.append(Paragraph("Answers", section))
    for idx, item in enumerate(task.get("questions", []), 1):
        story.append(Paragraph(f"{idx}. {item.get('question', '')}", normal))
        story.append(Paragraph(f"Answer: {item.get('answer', '')}", answer))

    _build_doc(filename, story)
    return filename


def _path(scope: TaskScope, task: dict, name: str) -> Path:
    out = reading_store.pdf_dir(scope, task["date"])
    out.mkdir(parents=True, exist_ok=True)
    return out / name


def _base_story(task: dict, title: str):
    styles = getSampleStyleSheet()
    font_name = register_cjk_font()
    title_style = ParagraphStyle("title", parent=styles["Heading1"], fontName=font_name,
                                 fontSize=16, spaceAfter=4)
    subtitle_style = ParagraphStyle("subtitle", parent=styles["Normal"], fontSize=10,
                                    fontName=font_name, textColor=colors.grey, spaceAfter=12)
    section_style = ParagraphStyle("section", parent=styles["Heading2"], fontSize=12,
                                   fontName=font_name, spaceBefore=14, spaceAfter=6)
    normal_style = ParagraphStyle("reading_normal", parent=styles["Normal"], fontSize=10,
                                  fontName=font_name, spaceAfter=8, leading=14)
    answer_style = ParagraphStyle("answer", parent=styles["Normal"], fontSize=10,
                                  fontName=font_name, textColor=colors.HexColor("#1a6b1a"),
                                  spaceAfter=5, leading=13)
    story = [
        Paragraph(title, title_style),
        Paragraph(f"{task['date']} | Grade {task.get('grade_level', '-')}", subtitle_style),
        HRFlowable(width="100%", thickness=0.5, color=colors.black),
        Spacer(1, 8),
    ]
    return story, {"section": section_style, "normal": normal_style, "answer": answer_style}


def _build_doc(filename: Path, story: list):
    doc = SimpleDocTemplate(str(filename), pagesize=letter,
                            rightMargin=0.75 * inch, leftMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    doc.build(story)

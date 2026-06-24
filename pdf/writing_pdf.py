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
    story, styles = _base_story(task, "Writing Memory Set")
    section = styles["section"]
    normal = styles["normal"]
    highlight = styles["highlight"]

    opinion = task.get("opinion", {})
    story.append(Paragraph("Opinion", section))
    story.append(Paragraph(paragraph_text(opinion.get("memorize_line") or opinion.get("claim", "")), highlight))
    if opinion.get("chinese"):
        story.append(Paragraph(paragraph_text(opinion.get("chinese")), normal))
    if opinion.get("sentence_frame"):
        story.append(Paragraph(f"Frame: {paragraph_text(opinion.get('sentence_frame'))}", normal))

    story.append(Paragraph("Three Examples to Memorize", section))
    for idx, item in enumerate(task.get("examples", []), 1):
        story.append(Paragraph(
            f"{idx}. <b>{paragraph_text(item.get('memorize_line', ''))}</b><br/>"
            f"{paragraph_text(item.get('chinese', ''))}<br/>"
            f"Why it works: {paragraph_text(item.get('why_it_works', ''))}",
            normal,
        ))

    story.append(Paragraph("Mini Outline", section))
    for item in task.get("mini_outline", []):
        story.append(Paragraph(f"- {paragraph_text(item)}", normal))

    rewrite = task.get("practice", {}).get("rewrite_task")
    if rewrite:
        story.append(Paragraph("Writing Practice", section))
        story.append(Paragraph(paragraph_text(rewrite), normal))

    _build_doc(filename, story)
    return filename


def build_answers(task: dict) -> Path:
    filename = _path(task, "answers.pdf")
    story, styles = _base_story(task, "Writing Memory Answer Key")
    section = styles["section"]
    normal = styles["normal"]
    answer = styles["answer"]

    story.append(Paragraph("Recitation Check", section))
    for item in task.get("practice", {}).get("recitation_check", []):
        story.append(Paragraph(paragraph_text(item.get("prompt", "")), normal))
        story.append(Paragraph(f"Answer: {paragraph_text(item.get('answer', ''))}", answer))

    story.append(Paragraph("Fill-in Practice", section))
    for idx, item in enumerate(task.get("examples", []), 1):
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

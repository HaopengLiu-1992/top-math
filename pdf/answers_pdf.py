from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib import colors

from storage.homework_store import pdf_dir

PART_LABELS = {
    "part1": "Part 1 - Warm-up: Basic Fluency",
    "part2": "Part 2 - Core Focus",
    "part3": "Part 3 - Real-world Word Problems",
}


def build(homework: dict) -> Path:
    date_str = homework["date"]
    out = pdf_dir(date_str)
    out.mkdir(parents=True, exist_ok=True)
    filename = out / "answers.pdf"

    doc = SimpleDocTemplate(str(filename), pagesize=letter,
                            rightMargin=0.75 * inch, leftMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=16, spaceAfter=4)
    subtitle_style = ParagraphStyle("subtitle", parent=styles["Normal"], fontSize=10,
                                    textColor=colors.grey, spaceAfter=12)
    section_style = ParagraphStyle("section", parent=styles["Heading2"], fontSize=12,
                                   spaceBefore=14, spaceAfter=6)
    question_style = ParagraphStyle("question", parent=styles["Normal"], fontSize=11,
                                    spaceAfter=4, leading=16)
    answer_style = ParagraphStyle("answer", parent=styles["Normal"], fontSize=11,
                                  textColor=colors.HexColor("#1a6b1a"), spaceAfter=4, leading=16)
    step_style = ParagraphStyle("step", parent=styles["Normal"], fontSize=10,
                                leftIndent=20, spaceAfter=3,
                                textColor=colors.HexColor("#2e5fa3"))

    story = []
    story.append(Paragraph(f"Answer Key - Day {homework['day']}", title_style))
    story.append(Paragraph(homework["date"], subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
    story.append(Spacer(1, 6))

    for part_key, label in PART_LABELS.items():
        questions = homework.get("parts", {}).get(part_key, [])
        if not questions:
            continue
        story.append(Paragraph(label, section_style))
        for i, q in enumerate(questions, 1):
            story.append(Paragraph(f"{i}. {q['question']}", question_style))
            story.append(Paragraph(f"   Answer: {q['answer']}", answer_style))
            for step in q.get("solution_steps", []):
                story.append(Paragraph(f"      {step}", step_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 6))

    challenge = homework.get("weekly_challenge")
    if challenge:
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Weekly Challenge Answer", section_style))
        story.append(Paragraph(challenge["question"], question_style))
        story.append(Paragraph(f"   Answer: {challenge['answer']}", answer_style))
        for step in challenge.get("solution_steps", []):
            story.append(Paragraph(f"      {step}", step_style))

    doc.build(story)
    return filename

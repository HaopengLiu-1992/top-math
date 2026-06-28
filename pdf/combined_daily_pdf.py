from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfWriter


@dataclass(frozen=True)
class PdfPart:
    label: str
    path: Path


def combined_pdf_dir(date_str: str) -> Path:
    y, m, d = date_str.split("-")
    return Path("output/tasks/combined/daily/pdf") / y / m / d


def build_today_all_pdf(date_str: str) -> tuple[Path | None, list[PdfPart], list[PdfPart]]:
    parts = _pdf_parts(date_str)
    return _build_combined_pdf(date_str, "today_all.pdf", parts)


def build_today_questions_pdf(date_str: str) -> tuple[Path | None, list[PdfPart], list[PdfPart]]:
    return _build_combined_pdf(date_str, "questions.pdf", _question_parts(date_str))


def build_today_answers_pdf(date_str: str) -> tuple[Path | None, list[PdfPart], list[PdfPart]]:
    return _build_combined_pdf(date_str, "answers.pdf", _answer_parts(date_str))


def _build_combined_pdf(date_str: str, filename: str,
                        parts: list[PdfPart]) -> tuple[Path | None, list[PdfPart], list[PdfPart]]:
    existing = [part for part in parts if part.path.exists()]
    missing = [part for part in parts if not part.path.exists()]
    if not existing:
        return None, existing, missing

    out_dir = combined_pdf_dir(date_str)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    writer = PdfWriter()
    for part in existing:
        writer.append(str(part.path))
    with open(out_path, "wb") as f:
        writer.write(f)

    return out_path, existing, missing


def _pdf_parts(date_str: str) -> list[PdfPart]:
    return _question_parts(date_str) + _answer_parts(date_str)


def _question_parts(date_str: str) -> list[PdfPart]:
    y, m, d = date_str.split("-")
    return [
        PdfPart("Math questions", Path("output/tasks/math/homework/pdf") / y / m / d / "questions.pdf"),
        PdfPart("Vocabulary questions", Path("output/tasks/english/vocabulary/pdf") / y / m / d / "vocabulary.pdf"),
        PdfPart("English reading questions", Path("output/tasks/english/reading/pdf") / y / m / d / "reading.pdf"),
        PdfPart("English writing questions", Path("output/tasks/english/writing/pdf") / y / m / d / "writing.pdf"),
        PdfPart("Science reading questions", Path("output/tasks/science/reading/pdf") / y / m / d / "reading.pdf"),
    ]


def _answer_parts(date_str: str) -> list[PdfPart]:
    y, m, d = date_str.split("-")
    return [
        PdfPart("Math answers", Path("output/tasks/math/homework/pdf") / y / m / d / "answers.pdf"),
        PdfPart("Vocabulary answers", Path("output/tasks/english/vocabulary/pdf") / y / m / d / "answers.pdf"),
        PdfPart("English reading answers", Path("output/tasks/english/reading/pdf") / y / m / d / "answers.pdf"),
        PdfPart("English writing answers", Path("output/tasks/english/writing/pdf") / y / m / d / "answers.pdf"),
        PdfPart("Science reading answers", Path("output/tasks/science/reading/pdf") / y / m / d / "answers.pdf"),
    ]

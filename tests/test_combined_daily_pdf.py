import os
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pdf.combined_daily_pdf import build_today_answers_pdf, build_today_questions_pdf


class CombinedDailyPdfTests(unittest.TestCase):
    def test_build_today_questions_and_answers_pdf_combines_existing_parts(self):
        cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                _write_pdf(Path("output/tasks/math/homework/pdf/2099/01/01/questions.pdf"), "math")
                _write_pdf(Path("output/tasks/math/homework/pdf/2099/01/01/answers.pdf"), "math answers")
                _write_pdf(Path("output/tasks/english/vocabulary/pdf/2099/01/01/vocabulary.pdf"), "vocab")
                _write_pdf(Path("output/tasks/english/vocabulary/pdf/2099/01/01/answers.pdf"), "vocab answers")

                questions_path, question_included, question_missing = build_today_questions_pdf("2099-01-01")
                answers_path, answer_included, answer_missing = build_today_answers_pdf("2099-01-01")

                self.assertIsNotNone(questions_path)
                self.assertTrue(questions_path.exists())
                self.assertEqual([part.label for part in question_included], ["Math questions", "Vocabulary questions"])
                self.assertGreaterEqual(len(question_missing), 1)
                self.assertEqual(len(PdfReader(str(questions_path)).pages), 2)

                self.assertIsNotNone(answers_path)
                self.assertTrue(answers_path.exists())
                self.assertEqual([part.label for part in answer_included], ["Math answers", "Vocabulary answers"])
                self.assertGreaterEqual(len(answer_missing), 1)
                self.assertEqual(len(PdfReader(str(answers_path)).pages), 2)
            finally:
                os.chdir(cwd)


def _write_pdf(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=letter)
    c.drawString(72, 720, text)
    c.save()


if __name__ == "__main__":
    unittest.main()

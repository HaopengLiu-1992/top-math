import os
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pdf.combined_daily_pdf import build_today_all_pdf


class CombinedDailyPdfTests(unittest.TestCase):
    def test_build_today_all_pdf_combines_existing_parts(self):
        cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                _write_pdf(Path("output/tasks/math/homework/pdf/2099/01/01/questions.pdf"), "math")
                _write_pdf(Path("output/tasks/english/vocabulary/pdf/2099/01/01/vocabulary.pdf"), "vocab")

                out_path, included, missing = build_today_all_pdf("2099-01-01")

                self.assertIsNotNone(out_path)
                self.assertTrue(out_path.exists())
                self.assertEqual([part.label for part in included], ["Math practice", "Vocabulary practice"])
                self.assertGreaterEqual(len(missing), 1)
                self.assertEqual(len(PdfReader(str(out_path)).pages), 2)
            finally:
                os.chdir(cwd)


def _write_pdf(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=letter)
    c.drawString(72, 720, text)
    c.save()


if __name__ == "__main__":
    unittest.main()

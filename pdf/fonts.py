from functools import lru_cache
import re
from xml.sax.saxutils import escape

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

CJK_FONT = "STSong-Light"
CJK_RE = re.compile(r"([\u2e80-\u9fff\uff00-\uffef]+)")


@lru_cache(maxsize=1)
def register_cjk_font() -> str:
    pdfmetrics.registerFont(UnicodeCIDFont(CJK_FONT))
    return CJK_FONT


def paragraph_text(value: object) -> str:
    """Escape text and apply the CJK font only to Chinese/CJK runs."""
    register_cjk_font()
    text = escape("" if value is None else str(value))
    return CJK_RE.sub(rf'<font name="{CJK_FONT}">\1</font>', text)

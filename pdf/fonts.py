from functools import lru_cache

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

CJK_FONT = "STSong-Light"


@lru_cache(maxsize=1)
def register_cjk_font() -> str:
    pdfmetrics.registerFont(UnicodeCIDFont(CJK_FONT))
    return CJK_FONT

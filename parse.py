from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextBox,LTRect

SPEARHEAD_WARSCROLL = "spearhead_warscroll"
WARSCROLL = "warscroll"
UNKNOWN = "unknown"

def page_type(page):
    for element in page:
        if not isinstance(element, LTTextBox):
            continue

        text = element.get_text()
        if "SPEARHEAD WARSCROLL" in text:
            return SPEARHEAD_WARSCROLL
            
        if "WARSCROLL" in text:
            return WARSCROLL

    return unknown

def get_name(page):
    """
    The unit name is always at the top of the scroll, and offset to the right
    """

    name = {}

    for element in page:
        if not isinstance(element, LTTextBox):
            continue

        mid_x = (element.x0 + element.x1) / 2
        if mid_x < 120:
            continue

        mid_y = (element.y0 + element.y1) / 2
        if mid_y < 380 or mid_y > 420:
            continue

        text = element.get_text()
        if "WARSCROLL" in text:
            continue

        name[mid_y] = " ".join(text.split())

    keys = list(name.keys())
    keys.sort(reverse=True)
    return ", ".join([name[k] for k in keys])

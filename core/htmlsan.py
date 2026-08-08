"""پاکسازی HTML خروجی ادیتور غنی با bleach — منبع واحد whitelist."""
import bleach

ALLOWED_TAGS = [
    'p', 'br', 'b', 'strong', 'i', 'em', 'u', 's', 'h2', 'h3', 'h4',
    'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'span', 'div', 'pre', 'code',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
]
ALLOWED_ATTRS = {
    'a': ['href', 'target', 'rel'],
    'img': ['src', 'alt', 'style', 'width', 'height'],
    'span': ['style'], 'div': ['style'], 'p': ['style'],
    'td': ['style', 'colspan', 'rowspan'], 'th': ['style', 'colspan', 'rowspan'],
    'table': ['style', 'border'],
}


def clean_html(html: str) -> str:
    return bleach.clean(html or '', tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)

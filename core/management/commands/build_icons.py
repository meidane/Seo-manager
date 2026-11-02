"""ساختِ اسپرایتِ آیکن‌ها (`static/img/icons.svg`) از فونت‌اوسامِ پرو (همان کتابخانه‌ای که کاربر داده — در
`worktracker/.../fontawesome_/webfonts/fa-regular-400.svg`). فقط آیکن‌های فهرستِ `core/icons.py: ICONS` برداشته می‌شوند.
استفاده: `{% icon 'trash' %}` در تمپلیت، `App.icon('trash')` در JS. آیکنِ تازه = اسم را به ICONS اضافه کن و همین را اجرا کن:
    python manage.py build_icons
"""
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.icons import ICONS

FONT_DIR = Path(settings.BASE_DIR) / 'worktracker' / 'worktracker' / 'static' / 'fonts' / 'fontawesome_' / 'webfonts'
OUT = Path(settings.BASE_DIR) / 'static' / 'img' / 'icons.svg'


class Command(BaseCommand):
    help = 'ساختِ static/img/icons.svg از فونت‌اوسامِ پرو'

    def handle(self, *args, **opts):
        fonts = {}
        for style, fname in (('regular', 'fa-regular-400.svg'), ('solid', 'fa-solid-900.svg')):
            src = (FONT_DIR / fname).read_text(encoding='utf-8')
            default_adv = int(re.search(r'<font[^>]*horiz-adv-x="(\d+)"', src).group(1))
            ascent = int(re.search(r'ascent="(-?\d+)"', src).group(1))
            glyphs = {}
            for m in re.finditer(r'<glyph\b([^>]*)/>', src):
                attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
                if 'glyph-name' in attrs and 'd' in attrs:
                    glyphs[attrs['glyph-name']] = (int(attrs.get('horiz-adv-x', default_adv)), attrs['d'])
            fonts[style] = (glyphs, ascent)
        out, missing = [], []
        for name, (fa_name, style) in ICONS.items():
            glyphs, ascent = fonts[style]
            if fa_name not in glyphs:
                missing.append(f'{name}→{fa_name}')
                continue
            adv, d = glyphs[fa_name]
            out.append(f'<symbol id="{name}" viewBox="0 0 {adv} 512"><path fill="currentColor" '
                       f'transform="translate(0 {ascent}) scale(1 -1)" d="{d}"/></symbol>')
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text('<svg xmlns="http://www.w3.org/2000/svg" style="display:none">' + ''.join(out) + '</svg>\n',
                       encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'{len(out)} آیکن → {OUT}'))
        if missing:
            self.stdout.write(self.style.WARNING('پیدا نشد: ' + ', '.join(missing)))

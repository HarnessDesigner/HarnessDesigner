# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
"""
Prepares installer image assets from source PNGs for the Windows Inno Setup build.

Run this before compiling installer_scripts/windows/harness_designer.iss.
Requires Pillow (already a project dependency; PySide6 not needed here).

Outputs to installer_scripts/windows/assets/:
  harness_designer.ico  — multi-size Windows icon (16, 32, 48, 64, 128, 256)
  installer_header.bmp  — 519×58 banner for the inner-page header strip
  wizard_panel.bmp      — 164×314 portrait panel for welcome / finish pages
"""
import os
from PIL import Image

_BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_IMAGE_DIR = os.path.join(_BASE, 'harness_designer', 'image')
_IMGS_DIR  = os.path.join(_IMAGE_DIR, 'images')
_OUT_DIR   = os.path.join(_BASE, 'installer_scripts', 'windows', 'assets')

# InnoSetup 6 modern-style wizard dimensions at 96 DPI
_WIZARD_W = 519   # full wizard-form client width
_HEADER_H = 58    # inner-page header strip height
_PANEL_W  = 164   # welcome/finish left-panel width
_PANEL_H  = 314   # welcome/finish left-panel height


def build_ico() -> None:
    """Build a multi-size .ico from the individual icon PNGs."""
    sizes = [16, 32, 48, 64, 128, 256]
    frames: list[Image.Image] = []
    for s in sizes:
        path = os.path.join(_IMAGE_DIR, f'icon_{s}x{s}.png')
        if not os.path.exists(path):
            # 48×48 is not a provided size — scale down from 64×64
            path = os.path.join(_IMAGE_DIR, 'icon_64x64.png')
        img = Image.open(path).convert('RGBA').resize((s, s), Image.LANCZOS)
        frames.append(img)

    out = os.path.join(_OUT_DIR, 'harness_designer.ico')
    frames[0].save(
        out,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f'  ico  → {out}')


def build_header_bmp() -> None:
    """Scale header_600x80.png to wizard width and centre-crop to header height."""
    img = Image.open(os.path.join(_IMGS_DIR, 'header_600x80.png')).convert('RGB')
    new_h = int(img.height * _WIZARD_W / img.width)
    img = img.resize((_WIZARD_W, new_h), Image.LANCZOS)
    if new_h > _HEADER_H:
        top = (new_h - _HEADER_H) // 2
        img = img.crop((0, top, _WIZARD_W, top + _HEADER_H))
    out = os.path.join(_OUT_DIR, 'installer_header.bmp')
    img.save(out, format='BMP')
    print(f'  bmp  → {out}')


def build_wizard_panel_bmp() -> None:
    """Scale large_splash.png to fill the portrait wizard-panel, centre-crop width."""
    img = Image.open(os.path.join(_IMGS_DIR, 'large_splash.png')).convert('RGB')
    # Scale so height fills the panel, then centre-crop to panel width
    new_w = int(img.width * _PANEL_H / img.height)
    img = img.resize((new_w, _PANEL_H), Image.LANCZOS)
    if new_w > _PANEL_W:
        left = (new_w - _PANEL_W) // 2
        img = img.crop((left, 0, left + _PANEL_W, _PANEL_H))
    elif new_w < _PANEL_W:
        canvas = Image.new('RGB', (_PANEL_W, _PANEL_H), (15, 15, 25))
        canvas.paste(img, ((_PANEL_W - new_w) // 2, 0))
        img = canvas
    out = os.path.join(_OUT_DIR, 'wizard_panel.bmp')
    img.save(out, format='BMP')
    print(f'  bmp  → {out}')


def prepare_all() -> None:
    """Prepare all installer image assets. Call before compiling harness_designer.iss."""
    os.makedirs(_OUT_DIR, exist_ok=True)
    print('Preparing installer assets...')
    build_ico()
    build_header_bmp()
    build_wizard_panel_bmp()
    print(f'Done. Assets written to: {_OUT_DIR}')

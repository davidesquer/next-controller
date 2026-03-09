from PIL import Image, ImageDraw, ImageFont
from StreamDeck.ImageHelpers import PILHelper


def _font(size: int = 28) -> ImageFont.FreeTypeFont:
    """Try to load a system font; fall back to PIL default."""
    for path in (
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_number(deck_dev, number: int) -> bytes:
    img = PILHelper.create_key_image(deck_dev, background="black")
    draw = ImageDraw.Draw(img)
    draw.text(
        (img.width / 2, img.height / 2),
        text=str(number),
        font=_font(36),
        anchor="mm",
        fill="white",
    )
    return PILHelper.to_native_key_format(deck_dev, img)


def make_folder(deck_dev, is_page_two: bool) -> bytes:
    img = PILHelper.create_key_image(deck_dev, background="black")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    pad = int(w * 0.15)
    folder_top = int(h * 0.25)
    tab_w = int(w * 0.35)
    tab_h = int(h * 0.10)
    color = "#f0c040" if not is_page_two else "#40a0f0"

    draw.rectangle([pad, folder_top - tab_h, pad + tab_w, folder_top], fill=color)
    draw.rectangle([pad, folder_top, w - pad, int(h * 0.72)], fill=color)

    label = "6-10" if is_page_two else "1-5"
    draw.text((w / 2, h * 0.88), text=label, font=_font(14), anchor="mm", fill="white")

    return PILHelper.to_native_key_format(deck_dev, img)


def make_lock(deck_dev) -> bytes:
    """Lock screen key — shows a lock icon."""
    img = PILHelper.create_key_image(deck_dev, background="black")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    # Simple padlock shape
    cx, cy = w // 2, h // 2
    body_w, body_h = int(w * 0.45), int(h * 0.30)
    arc_r = int(w * 0.18)

    # Shackle (arc)
    draw.arc(
        [cx - arc_r, cy - body_h - arc_r, cx + arc_r, cy - body_h + arc_r + 4],
        start=0, end=180, fill="#888888", width=3,
    )
    # Body
    draw.rectangle(
        [cx - body_w // 2, cy - body_h // 2, cx + body_w // 2, cy + body_h // 2],
        fill="#888888",
    )

    return PILHelper.to_native_key_format(deck_dev, img)


def make_scan_prompt(deck_dev) -> bytes:
    """Shows 'SCAN' text for the lock screen."""
    img = PILHelper.create_key_image(deck_dev, background="black")
    draw = ImageDraw.Draw(img)
    draw.text(
        (img.width / 2, img.height / 2),
        text="SCAN",
        font=_font(18),
        anchor="mm",
        fill="#00cc66",
    )
    return PILHelper.to_native_key_format(deck_dev, img)


def make_text(deck_dev, text: str, color: str = "white", bg: str = "black") -> bytes:
    """Generic text key."""
    img = PILHelper.create_key_image(deck_dev, background=bg)
    draw = ImageDraw.Draw(img)
    draw.text(
        (img.width / 2, img.height / 2),
        text=text,
        font=_font(14),
        anchor="mm",
        fill=color,
    )
    return PILHelper.to_native_key_format(deck_dev, img)


def make_red(deck_dev) -> bytes:
    img = PILHelper.create_key_image(deck_dev, background="red")
    return PILHelper.to_native_key_format(deck_dev, img)

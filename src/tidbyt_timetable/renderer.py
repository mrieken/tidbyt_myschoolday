"""Native-resolution pixel renderer for the five-lesson display."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Sequence

from PIL import Image, ImageDraw

WIDTH = 64
HEIGHT = 32
BACKGROUND = (9, 13, 16)
ROW_FILL = (15, 20, 23)
SEPARATOR = (27, 33, 36)
NUMBER_COLOR = (205, 211, 211)
UNKNOWN_COLOR = (130, 139, 141)
ROW_TOPS = (1, 7, 13, 19, 25)

FONT: dict[str, tuple[str, ...]] = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("110", "001", "010", "100", "111"),
    "3": ("110", "001", "010", "001", "110"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "110", "001", "110"),
    "6": ("011", "100", "110", "101", "010"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("010", "101", "010", "101", "010"),
    "9": ("010", "101", "011", "001", "110"),
    "A": ("010", "101", "111", "101", "101"),
    "B": ("110", "101", "110", "101", "110"),
    "C": ("011", "100", "100", "100", "011"),
    "D": ("110", "101", "101", "101", "110"),
    "E": ("111", "100", "110", "100", "111"),
    "F": ("111", "100", "110", "100", "100"),
    "G": ("011", "100", "101", "101", "011"),
    "H": ("101", "101", "111", "101", "101"),
    "I": ("111", "010", "010", "010", "111"),
    "J": ("001", "001", "001", "101", "010"),
    "K": ("101", "101", "110", "101", "101"),
    "L": ("100", "100", "100", "100", "111"),
    "M": ("101", "111", "111", "101", "101"),
    "N": ("101", "111", "111", "111", "101"),
    "O": ("010", "101", "101", "101", "010"),
    "P": ("110", "101", "110", "100", "100"),
    "Q": ("010", "101", "101", "111", "011"),
    "R": ("110", "101", "110", "101", "101"),
    "S": ("011", "100", "010", "001", "110"),
    "T": ("111", "010", "010", "010", "010"),
    "U": ("101", "101", "101", "101", "111"),
    "V": ("101", "101", "101", "101", "010"),
    "W": ("101", "101", "111", "111", "101"),
    "X": ("101", "101", "010", "101", "101"),
    "Y": ("101", "101", "010", "010", "010"),
    "Z": ("111", "001", "010", "100", "111"),
    "-": ("000", "000", "111", "000", "000"),
}


@dataclass(frozen=True)
class DisplayLesson:
    name: str
    color: tuple[int, int, int]


def _draw_text(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, color: tuple[int, int, int]) -> None:
    for character_index, character in enumerate(text.upper()):
        glyph = FONT.get(character)
        if glyph is None:
            raise ValueError(f"Unsupported display character: {character!r}")
        character_x = x + character_index * 4
        for row_index, row in enumerate(glyph):
            for column_index, pixel in enumerate(row):
                if pixel == "1":
                    draw.point((character_x + column_index, y + row_index), fill=color)


def render_timetable(lessons: Sequence[DisplayLesson]) -> Image.Image:
    if len(lessons) != 5:
        raise ValueError(f"Exactly five lesson slots are required, got {len(lessons)}")

    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    for index, (lesson, top) in enumerate(zip(lessons, ROW_TOPS, strict=True)):
        draw.rectangle((0, top, WIDTH - 1, top + 4), fill=ROW_FILL)
        _draw_text(draw, str(index + 1), 4, top, NUMBER_COLOR)
        if lesson.name:
            _draw_text(draw, lesson.name, 15, top, lesson.color)
        if index < 4:
            draw.line((0, top + 5, WIDTH - 1, top + 5), fill=SEPARATOR)

    return image


def encode_static_webp(image: Image.Image) -> bytes:
    if image.size != (WIDTH, HEIGHT):
        raise ValueError(f"Upload image must be {WIDTH}x{HEIGHT}, got {image.width}x{image.height}")
    buffer = BytesIO()
    image.save(buffer, format="WEBP", lossless=True, quality=100, method=6)
    data = buffer.getvalue()
    with Image.open(BytesIO(data)) as decoded:
        if decoded.size != (WIDTH, HEIGHT) or getattr(decoded, "n_frames", 1) != 1:
            raise ValueError("Encoded upload must be a static 64x32 WebP")
    return data
from io import BytesIO

import pytest
from PIL import Image

from tidbyt_timetable.renderer import (
    HEIGHT,
    ROW_FILL,
    ROW_TOPS,
    WIDTH,
    DisplayLesson,
    encode_static_webp,
    render_timetable,
)

LESSONS = [
    DisplayLesson("Deutsch", (140, 170, 196)),
    DisplayLesson("Sport", (141, 174, 155)),
    DisplayLesson("Mathe", (197, 172, 129)),
    DisplayLesson("Englisch", (170, 160, 190)),
    DisplayLesson("", (130, 139, 141)),
]


def test_native_render_has_five_identical_full_width_rows_and_blank_fifth_subject():
    image = render_timetable(LESSONS)

    assert image.size == (WIDTH, HEIGHT) == (64, 32)
    assert len(ROW_TOPS) == 5
    assert all(image.getpixel((63, top + 2)) == ROW_FILL for top in ROW_TOPS)
    for lesson, top in zip(LESSONS[:4], ROW_TOPS[:4], strict=True):
        assert any(image.getpixel((x, y)) == lesson.color for x in range(15, 23) for y in range(top, top + 5))
    assert all(
        image.getpixel((x, y)) != LESSONS[4].color
        for x in range(15, WIDTH)
        for y in range(ROW_TOPS[4], ROW_TOPS[4] + 5)
    )
    assert image.tobytes() == render_timetable(LESSONS).tobytes()


def test_webp_is_static_and_native_resolution():
    encoded = encode_static_webp(render_timetable(LESSONS))

    with Image.open(BytesIO(encoded)) as decoded:
        assert decoded.format == "WEBP"
        assert decoded.size == (64, 32)
        assert decoded.n_frames == 1


def test_renderer_rejects_more_or_fewer_than_five_slots():
    with pytest.raises(ValueError, match="Exactly five"):
        render_timetable(LESSONS[:4])
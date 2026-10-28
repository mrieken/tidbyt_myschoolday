import base64
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
import requests
from PIL import Image

from tidbyt_timetable.renderer import DisplayLesson, render_timetable
from tidbyt_timetable.tidbyt_api import TidbytApiError, TidbytClient

TOKEN = "never-log-this-token"
IMAGE = render_timetable([DisplayLesson("Deutsch", (140, 170, 196))] * 4 + [DisplayLesson("", (130, 139, 141))])


def test_publish_posts_exact_background_installation_and_static_webp():
    response = Mock(status_code=200)
    with patch("tidbyt_timetable.tidbyt_api.requests.post", return_value=response) as post:
        TidbytClient("device id", TOKEN).publish(IMAGE, "school-timetable")

    post.assert_called_once()
    args, kwargs = post.call_args
    assert args[0] == "https://api.tidbyt.com/v0/devices/device%20id/push"
    assert kwargs["headers"] == {"Authorization": f"Bearer {TOKEN}"}
    assert kwargs["allow_redirects"] is False
    body = kwargs["json"]
    assert body["deviceID"] == "device id"
    assert body["installationID"] == "school-timetable"
    assert body["background"] is True
    with Image.open(BytesIO(base64.b64decode(body["image"]))) as decoded:
        assert decoded.format == "WEBP"
        assert decoded.size == (64, 32)
        assert decoded.n_frames == 1


@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
def test_publish_http_errors_fail_without_leaking_token(status_code):
    with patch("tidbyt_timetable.tidbyt_api.requests.post", return_value=Mock(status_code=status_code)) as post:
        with pytest.raises(TidbytApiError, match=f"HTTP {status_code}") as error:
            TidbytClient("device", TOKEN).publish(IMAGE, "school-timetable")

    post.assert_called_once()
    assert TOKEN not in str(error.value)


def test_publish_timeout_fails_without_retry():
    with patch("tidbyt_timetable.tidbyt_api.requests.post", side_effect=requests.Timeout) as post:
        with pytest.raises(TidbytApiError, match="timed out"):
            TidbytClient("device", TOKEN).publish(IMAGE, "school-timetable")
    post.assert_called_once()


def test_remove_quotes_installation_id_and_accepts_success():
    with patch("tidbyt_timetable.tidbyt_api.requests.delete", return_value=Mock(status_code=200)) as delete:
        assert TidbytClient("device", TOKEN).remove("school timetable/1")

    delete.assert_called_once()
    assert delete.call_args.args[0].endswith("/installations/school%20timetable%2F1")
    assert delete.call_args.kwargs["allow_redirects"] is False


def test_remove_404_is_successful_noop_and_other_errors_fail():
    with patch("tidbyt_timetable.tidbyt_api.requests.delete", return_value=Mock(status_code=404)) as delete:
        assert not TidbytClient("device", TOKEN).remove("school-timetable")
    delete.assert_called_once()

    with patch("tidbyt_timetable.tidbyt_api.requests.delete", return_value=Mock(status_code=500)) as delete:
        with pytest.raises(TidbytApiError, match="HTTP 500"):
            TidbytClient("device", TOKEN).remove("school-timetable")
    delete.assert_called_once()


def test_remove_timeout_fails_without_retry():
    with patch("tidbyt_timetable.tidbyt_api.requests.delete", side_effect=requests.Timeout) as delete:
        with pytest.raises(TidbytApiError, match="timed out"):
            TidbytClient("device", TOKEN).remove("school-timetable")
    delete.assert_called_once()
"""Single-attempt client for the Tidbyt device REST API."""

from __future__ import annotations

import base64
from urllib.parse import quote

import requests
from PIL import Image

from tidbyt_timetable.renderer import encode_static_webp

API_ROOT = "https://api.tidbyt.com/v0/devices"
TIMEOUT_SECONDS = 20


class TidbytApiError(RuntimeError):
    """Raised when a Tidbyt API operation fails."""


class TidbytClient:
    def __init__(self, device_id: str, api_token: str, timeout: int = TIMEOUT_SECONDS):
        if not device_id.strip():
            raise ValueError("TIDBYT_DEVICE_ID is missing")
        if not api_token.strip():
            raise ValueError("TIDBYT_API_TOKEN is missing")
        self.device_id = device_id
        self._api_token = api_token
        self.timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_token}"}

    def _error_detail(self, response: requests.Response) -> str:
        detail = ""
        try:
            payload = response.json()
        except (ValueError, requests.RequestException):
            payload = None
        if isinstance(payload, dict):
            for key in ("message", "error", "detail"):
                value = payload.get(key)
                if isinstance(value, str):
                    detail = value
                    break
                if isinstance(value, dict) and isinstance(value.get("message"), str):
                    detail = value["message"]
                    break
        if not detail:
            body = response.text
            if isinstance(body, str):
                detail = body
        for sensitive_value in (self._api_token, self.device_id):
            detail = detail.replace(sensitive_value, "[redacted]")
        return " ".join(detail.split())[:400]

    def _http_error(self, operation: str, response: requests.Response) -> TidbytApiError:
        message = f"Tidbyt {operation} failed with HTTP {response.status_code}"
        detail = self._error_detail(response)
        if detail:
            message = f"{message}: {detail}"
        return TidbytApiError(message)

    def publish(self, image: Image.Image, installation_id: str) -> None:
        image_data = base64.b64encode(encode_static_webp(image)).decode("ascii")
        url = f"{API_ROOT}/{quote(self.device_id, safe='')}/push"
        body = {
            "deviceID": self.device_id,
            "image": image_data,
            "installationID": installation_id,
            "background": True,
        }
        try:
            response = requests.post(
                url,
                headers=self._headers,
                json=body,
                timeout=self.timeout,
                allow_redirects=False,
            )
        except requests.Timeout as error:
            raise TidbytApiError("Tidbyt publish request timed out") from error
        except requests.RequestException as error:
            raise TidbytApiError("Tidbyt publish request failed") from error
        if response.status_code != 200:
            raise self._http_error("publish", response)

    def remove(self, installation_id: str) -> bool:
        url = (
            f"{API_ROOT}/{quote(self.device_id, safe='')}/installations/"
            f"{quote(installation_id, safe='')}"
        )
        try:
            response = requests.delete(
                url,
                headers=self._headers,
                timeout=self.timeout,
                allow_redirects=False,
            )
        except requests.Timeout as error:
            raise TidbytApiError("Tidbyt removal request timed out") from error
        except requests.RequestException as error:
            raise TidbytApiError("Tidbyt removal request failed") from error
        if response.status_code == 404:
            return False
        if response.status_code not in (200, 204):
            raise self._http_error("removal", response)
        return True
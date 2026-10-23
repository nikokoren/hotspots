"""Small stdlib HTTP helper with timeouts and retries."""

from __future__ import annotations

import time
import urllib.request

USER_AGENT = "hotspots-volcano-watch/0.1 (+https://github.com/nikokoren/hotspots)"


def get(url: str, timeout_s: float = 60, retries: int = 3, backoff_s: float = 2.0) -> bytes:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - network errors vary widely
            last = exc
            if attempt < retries:
                time.sleep(backoff_s * 2**attempt)
    raise RuntimeError(f"GET failed after {retries + 1} attempts: {redact(url)}: {last}")


def redact(url: str) -> str:
    """Strip a FIRMS MAP_KEY path segment so it never reaches logs."""
    marker = "/api/area/csv/"
    if marker in url:
        head, tail = url.split(marker, 1)
        parts = tail.split("/", 1)
        return f"{head}{marker}***/{parts[1] if len(parts) > 1 else ''}"
    return url

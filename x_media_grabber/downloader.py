"""Streaming file downloader: resume-safe skip, retries, size cap."""

import time
import urllib.request

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class _TooBig(Exception):
    pass


def _remove(path):
    try:
        path.unlink()
    except OSError:
        pass


def download(url, dest, timeout=60, retries=3, max_mb=0, file_sleep=0.3):
    """Download ``url`` to ``dest``.

    Returns: "ok" | "skip" (already exists) | "skip-big" (over size cap)
             | "fail" (all retries exhausted; partial file removed).
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return "skip"
    cap = max_mb * 1024 * 1024 if max_mb else 0
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                total = resp.headers.get("Content-Length")
                if cap and total and int(total) > cap:
                    return "skip-big"
                size = 0
                with open(dest, "wb") as f:
                    while True:
                        chunk = resp.read(256 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        if cap and size > cap:
                            raise _TooBig()
                        f.write(chunk)
            time.sleep(file_sleep)
            return "ok"
        except _TooBig:
            _remove(dest)
            return "skip-big"
        except Exception:
            _remove(dest)
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    return "fail"

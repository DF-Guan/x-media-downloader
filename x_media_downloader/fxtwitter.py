"""Fetch public X media timelines via the FxTwitter mirror API.

No X login / cookies required. Each post keeps its original
tweet id + timestamp so file naming stays traceable.
"""

import json
import time
import urllib.request

API_BASE = "https://api.fxtwitter.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _get_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def fetch_media_posts(handle, want=20, page_size=20, page_sleep=1.0, timeout=30):
    """Return newest media posts for ``handle``.

    Each item: ``{"id": tweet_id, "created": unix_ts, "media": [{"type", "url"}]}``.
    ``want``: number of media posts to collect; ``want <= 0`` means "all
    available" (paginate until the timeline is exhausted).
    """
    posts, cursor, seen = [], None, set()
    while True:
        if want > 0 and len(posts) >= want:
            break
        url = f"{API_BASE}/2/profile/{handle}/media?count={page_size}"
        if cursor:
            url += f"&cursor={cursor}"
        data = _get_json(url, timeout=timeout)
        results = data.get("results") or []
        if not results:
            break
        for item in results:
            tid = str(item.get("id") or "")
            if not tid or tid in seen:
                continue
            seen.add(tid)
            media = [
                {"type": m.get("type", "photo"), "url": m.get("url", "")}
                for m in ((item.get("media") or {}).get("all") or [])
                if m.get("url")
            ]
            if not media:  # text-only post, skip
                continue
            posts.append(
                {
                    "id": tid,
                    "created": item.get("created_timestamp") or 0,
                    "media": media,
                }
            )
            if want > 0 and len(posts) >= want:
                break
        cur = (data.get("cursor") or {}).get("bottom")
        if not cur or cur == cursor:
            break
        cursor = cur
        time.sleep(page_sleep)
    return posts[:want] if want > 0 else posts

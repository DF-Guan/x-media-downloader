"""Job orchestrator: N accounts x M posts -> folders + manifest + summary."""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .downloader import download
from .fxtwitter import fetch_media_posts
from .naming import render, sanitize, validate_template

IMAGE_EXTS = {"jpg", "png", "webp", "gif"}


def ext_from_url(url, kind):
    base = url.split("?")[0]
    ext = base.rsplit(".", 1)[-1].lower() if "." in base else ""
    if kind != "photo" or ext in ("mp4", "mov", "m3u8"):
        return "mov" if ext == "mov" else "mp4"
    return ext if ext in IMAGE_EXTS else "jpg"


def media_kind(mtype):
    return "image" if mtype == "photo" else "video"


def run(cfg, progress=None):
    """Run a download job.

    ``cfg`` keys: handles, posts (<=0 = all), media_types ("image"/"video"/"all"),
    dir_template, file_template, seq_width, out_dir, tz_offset, page_sleep,
    user_sleep, file_sleep, timeout, retries, max_mb, dry_run.
    ``progress``: optional callback receiving dict events.
    Returns the summary dict (also written to summary.json).
    """
    validate_template(cfg.get("dir_template", "{handle}"), "dir")
    validate_template(cfg.get("file_template",
                              "{handle}_{date}_{tweet_id}_{seq}.{ext}"), "file")

    def emit(**kw):
        if progress:
            progress(kw)

    tz = timezone(timedelta(hours=cfg.get("tz_offset", 8)))
    out = Path(cfg.get("out_dir", "downloads"))
    out.mkdir(parents=True, exist_ok=True)
    want = cfg.get("posts", 20)
    media_types = cfg.get("media_types", "all")
    seq_width = cfg.get("seq_width", 2)
    dry_run = cfg.get("dry_run", False)

    manifest_path = out / "manifest.jsonl"
    manifest = open(manifest_path, "a", encoding="utf-8")
    summary = {}
    handles = cfg.get("handles", [])
    for idx, acc in enumerate(handles, 1):
        handle, name = acc["handle"], acc.get("name", "")
        emit(phase="fetch", user=idx, total_users=len(handles), handle=handle)
        try:
            posts = fetch_media_posts(handle, want=want,
                                      page_sleep=cfg.get("page_sleep", 1.0),
                                      timeout=cfg.get("timeout", 30))
        except Exception as exc:  # noqa: BLE001 - keep job going
            summary[handle] = {"posts": 0, "downloaded": 0, "skipped": 0,
                               "failed": 0, "filtered": 0, "error": str(exc)}
            emit(phase="user-done", user=idx, total_users=len(handles),
                 handle=handle, error=str(exc))
            continue
        counts = {"downloaded": 0, "skipped": 0, "failed": 0, "filtered": 0}
        for item in posts:
            dt = (datetime.fromtimestamp(item["created"], tz=tz)
                  if item["created"] else None)
            base = {
                "handle": handle, "name": name or handle,
                "date": dt.strftime("%Y%m%d") if dt else "nodate",
                "date_dash": dt.strftime("%Y-%m-%d") if dt else "nodate",
                "time": dt.strftime("%H%M%S") if dt else "notime",
                "tweet_id": item["id"],
            }
            for n, m in enumerate(item["media"], 1):
                kind = media_kind(m["type"])
                if media_types != "all" and kind != media_types:
                    counts["filtered"] += 1
                    continue
                ext = ext_from_url(m["url"], m["type"])
                fname = sanitize(render(cfg["file_template"],
                                        {**base, "seq": n, "ext": ext, "type": kind},
                                        seq_width))
                dname = sanitize(render(cfg["dir_template"],
                                        {"handle": handle, "name": name or handle}))
                dest = out / dname / fname
                if dry_run:
                    status = "planned"
                else:
                    status = download(m["url"], dest,
                                      timeout=cfg.get("timeout", 60),
                                      retries=cfg.get("retries", 3),
                                      max_mb=cfg.get("max_mb", 0),
                                      file_sleep=cfg.get("file_sleep", 0.3))
                    counts["downloaded" if status == "ok" else
                           "skipped" if status in ("skip", "skip-big") else "failed"] += 1
                manifest.write(json.dumps({"handle": handle, "tweet_id": item["id"],
                                           "url": m["url"], "file": str(dest),
                                           "status": status}, ensure_ascii=False) + "\n")
                manifest.flush()
                emit(phase="file", user=idx, total_users=len(handles),
                     handle=handle, file=fname, status=status)
        summary[handle] = {"posts": len(posts), **counts}
        emit(phase="user-done", user=idx, total_users=len(handles),
             handle=handle, posts=len(posts), **counts)
        time.sleep(cfg.get("user_sleep", 2.0))
    manifest.close()
    with open(out / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    emit(phase="done", summary=summary)
    return summary

#!/usr/bin/env python3
"""x-media-grabber CLI. Zero third-party dependencies.

Examples:
  python grab.py download --handles Anaimiya,waifupupu --posts 20
  python grab.py download --archive https://img.example.com/data/archive.json --top 15 --posts 20
  python grab.py download --handles-file handles.txt --posts 0 --media-types image
  python grab.py validate --dir-template "{handle}" --file-template "{handle}_{date}_{tweet_id}_{seq}.{ext}"
  python grab.py serve --port 8765
"""

import argparse
import json
import sys
from pathlib import Path

from x_media_grabber.jobs import run
from x_media_grabber.naming import DIR_VARS, FILE_VARS, validate_template
from x_media_grabber.sources import load_handles

DEFAULTS = {
    "posts": 20,
    "media_types": "all",
    "dir_template": "{handle}",
    "file_template": "{handle}_{date}_{tweet_id}_{seq}.{ext}",
    "seq_width": 2,
    "out_dir": "downloads",
    "tz_offset": 8,
    "page_sleep": 1.0,
    "user_sleep": 2.0,
    "file_sleep": 0.3,
    "timeout": 60,
    "retries": 3,
    "max_mb": 0,
    "dry_run": False,
}


def build_parser():
    p = argparse.ArgumentParser(description="Download public X media posts (no login).")
    p.add_argument("--config", help="JSON config file (CLI flags override it)")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("download", help="Run a download job")
    d.add_argument("--handles", help="Comma-separated handles, e.g. a,b,c")
    d.add_argument("--handles-file", help="txt (one per line) or json list")
    d.add_argument("--archive", help="archive.json path or URL (ranked source)")
    d.add_argument("--top", type=int, default=0, help="Take top N from archive (0 = all)")
    d.add_argument("--offset", type=int, default=0, help="Skip first N of archive ranking")
    d.add_argument("--include-suspended", action="store_true")
    d.add_argument("--posts", type=int, default=20, help="Media posts per account; 0 = all available")
    d.add_argument("--media-types", choices=["all", "image", "video"], default="all")
    d.add_argument("--out-dir", default="downloads")
    d.add_argument("--dir-template", default=DEFAULTS["dir_template"])
    d.add_argument("--file-template", default=DEFAULTS["file_template"])
    d.add_argument("--seq-width", type=int, default=2)
    d.add_argument("--tz-offset", type=int, default=8, help="UTC offset for {date}, e.g. 8 = Beijing")
    d.add_argument("--max-mb", type=int, default=0, help="Skip files larger than this (0 = no limit)")
    d.add_argument("--dry-run", action="store_true", help="List only, download nothing")

    v = sub.add_parser("validate", help="Validate naming templates")
    v.add_argument("--dir-template", default=DEFAULTS["dir_template"])
    v.add_argument("--file-template", default=DEFAULTS["file_template"])

    s = sub.add_parser("serve", help="Run local HTTP API + demo page (for webpage merge)")
    s.add_argument("--port", type=int, default=8765)
    return p


def cmd_validate(args):
    try:
        validate_template(args.dir_template, "dir")
        validate_template(args.file_template, "file")
    except ValueError as exc:
        print(f"INVALID: {exc}")
        return 1
    print("OK: templates valid")
    print(f"  dir vars : {list(DIR_VARS)}")
    print(f"  file vars: {list(FILE_VARS)}")
    return 0


def cmd_download(args, base_cfg):
    cfg = dict(base_cfg)
    for key in DEFAULTS:
        val = getattr(args, key, None)
        if isinstance(val, bool):
            if val:
                cfg[key] = val
        elif val is not None:
            cfg[key] = val
    # argparse uses out_dir attr for --out-dir
    cfg["out_dir"] = args.out_dir or cfg.get("out_dir", "downloads")
    handles = load_handles(
        handles=args.handles.split(",") if args.handles else None,
        handles_file=args.handles_file,
        archive=args.archive,
        top=args.top, offset=args.offset,
        include_suspended=args.include_suspended,
    )
    if not handles:
        print("No accounts selected. Use --handles / --handles-file / --archive.")
        return 2
    cfg["handles"] = handles
    print(f"Accounts: {len(handles)}, posts each: "
          f"{cfg['posts'] if cfg['posts'] > 0 else 'ALL'}")

    def progress(ev):
        if ev.get("phase") == "user-done":
            print(f"[{ev['user']}/{ev['total_users']}] @{ev['handle']}: "
                  f"posts={ev.get('posts', '?')} ok={ev.get('downloaded', 0)} "
                  f"skip={ev.get('skipped', 0)} fail={ev.get('failed', 0)}")
        elif ev.get("phase") == "file" and ev.get("status") == "fail":
            print(f"  FAIL {ev.get('file')}")

    summary = run(cfg, progress=progress)
    ok = sum(1 for s in summary.values() if not s.get("error"))
    print(f"Done: {ok}/{len(summary)} accounts, see {Path(cfg['out_dir']) / 'summary.json'}")
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    base_cfg = dict(DEFAULTS)
    if getattr(args, "config", None):
        with open(args.config, encoding="utf-8") as f:
            base_cfg.update(json.load(f))
    if args.cmd == "validate":
        return cmd_validate(args)
    if args.cmd == "serve":
        from server import serve
        serve(args.port)
        return 0
    return cmd_download(args, base_cfg)


if __name__ == "__main__":
    sys.exit(main())

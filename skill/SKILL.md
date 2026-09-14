---
name: x-media-grabber
description: Download public X (Twitter) media posts without login - single account, TopN from archive.json, or full lists. Editable-but-constrained folder/file naming templates. Use when the user wants to batch-download images/videos from X creators.
---

# x-media-grabber

Batch-download public X creator media (images + videos) with **no X login required**
(via FxTwitter mirror API). Single account, TopN, or full-archive runs.
Naming is editable through constrained `{variable}` templates so a webpage
can expose them as fixed dropdowns.

## When to use

- User wants images/videos from one or more X handles
- User wants "Top N creators" from an `archive.json` gallery source
- User wants custom folder / filename formats

## Quick recipes (run inside the repo dir)

Single account, 20 newest media posts:

```bash
python grab.py download --handles Anaimiya --posts 20
```

One account, everything available (posts=0 means "download all"):

```bash
python grab.py download --handles Anaimiya --posts 0 --out ./downloads
```

Images only, custom naming:

```bash
python grab.py download --handles a,b,c --posts 20 --media-types image \
  --dir-template "{handle}" \
  --file-template "{handle}_{date_dash}_{tweet_id}_{seq}.{ext}"
```

Top 15 from a gallery archive source:

```bash
python grab.py download --archive https://host/data/archive.json --top 15 --posts 20
```

Preview without downloading:

```bash
python grab.py download --handles Anaimiya --posts 5 --dry-run
```

Validate templates before a run:

```bash
python grab.py validate --dir-template "{handle}" \
  --file-template "{handle}_{date}_{tweet_id}_{seq}.{ext}"
```

## Naming variables (constrained whitelist)

- Folder: `{handle}` `{name}`
- File: `{handle}` `{name}` `{date}`(YYYYMMDD) `{date_dash}`(YYYY-MM-DD)
  `{time}`(HHMMSS) `{tweet_id}` `{seq}`(media index in post, zero-padded)
  `{ext}` `{type}`(image|video)
- File template must contain `{ext}`. Illegal filesystem chars are auto-replaced.

## Outputs

- `downloads/<folder>/` media files
- `downloads/manifest.jsonl` - one JSON line per file (handle, tweet_id, url, status)
- `downloads/summary.json` - per-account counts

Existing non-empty files are skipped, so interrupted jobs resume safely.

## Webpage integration

```bash
python grab.py serve --port 8765   # API + demo page at http://127.0.0.1:8765
```

- `GET /api/templates` - variable whitelist + defaults (for building dropdowns)
- `POST /api/validate` - check templates before starting
- `POST /api/jobs` - start job (`handles[]` or `archive`+`top`, `posts` 0=all, ...)
- `GET /api/jobs/<id>` - poll progress (`done_users/total_users/current`, `summary` at end)

See `web/index.html` for a minimal merge-ready example.

## Limits & notes

- Public posts only;boards on the mirror API's availability/rate limits.
- Keep `page_sleep`/`user_sleep` polite; use `--max-mb` to cap file size.
- Media belongs to the original creators; archive for personal use only.

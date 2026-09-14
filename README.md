# x-media-grabber

Batch-download **public** X (Twitter) creator media — images + videos — with **no X login required**
(via the FxTwitter mirror API). Zero third-party dependencies (Python stdlib only).

- 1 account, N accounts, TopN from `archive.json`, or a full list
- Posts per account configurable; `0` = download all available ("超了就全下")
- Editable folder / file naming via constrained `{variable}` templates
- Resume-safe (existing files skipped), `manifest.jsonl` + `summary.json` outputs
- Local HTTP API + demo page, ready to merge into your own website
- Agent skill included (`skill/SKILL.md`)

## Quickstart

```bash
# single account, 20 newest media posts
python grab.py download --handles Anaimiya --posts 20

# one account, everything available
python grab.py download --handles Anaimiya --posts 0

# images only + custom naming
python grab.py download --handles a,b,c --posts 20 --media-types image \
  --dir-template "{handle}" \
  --file-template "{handle}_{date_dash}_{tweet_id}_{seq}.{ext}"

# Top 15 from a gallery archive source
python grab.py download --archive https://host/data/archive.json --top 15 --posts 20

# dry-run: list only, download nothing
python grab.py download --handles Anaimiya --posts 5 --dry-run
```

Full options in `config.example.json` (pass with `--config config.json`; CLI flags override it).

## Naming templates

| scope   | allowed variables |
|---------|-------------------|
| folder  | `{handle}` `{name}` |
| file    | `{handle}` `{name}` `{date}` `{date_dash}` `{time}` `{tweet_id}` `{seq}` `{ext}` `{type}` |

- `{date}` = YYYYMMDD (default tz UTC+8, change with `--tz-offset`), `{time}` = HHMMSS
- `{seq}` = media index inside one post, zero-padded (`--seq-width`, default 2)
- `{type}` = image / video. File template must contain `{ext}`.
- Illegal filename chars are sanitized automatically; name clashes are skipped, never overwritten.

Validate first: `python grab.py validate --file-template "..."` (webpage: `POST /api/validate`).

## Webpage integration

```bash
python grab.py serve --port 8765   # demo page: http://127.0.0.1:8765
```

| endpoint | use |
|---|---|
| `GET /api/templates` | variable whitelist + defaults → build fixed dropdowns |
| `POST /api/validate` | check templates before starting a job |
| `POST /api/jobs` | start job: `handles[]` or `archive`+`top`, `posts` (0=all), `media_types`, templates… → `{id}` |
| `GET /api/jobs` / `GET /api/jobs/<id>` | poll progress (`done_users/total_users/current`), `summary` when done |

`web/index.html` is a minimal vanilla-JS example to copy into your site.

## Project layout

```
grab.py                 CLI (download / validate / serve)
server.py               local HTTP API + static demo page
config.example.json     all options with defaults
x_media_grabber/        core library (importable, zero deps)
  fxtwitter.py          mirror-API client (pagination)
  sources.py            handles list / txt / archive.json
  naming.py             template whitelist + sanitize
  downloader.py         streaming download, retry, size cap
  jobs.py               N accounts x M posts orchestrator
web/index.html          merge-ready demo UI
skill/SKILL.md          agent skill
```

## Notes

- Public posts only; subject to the mirror API's availability and rate limits.
  Keep sleeps polite; `--max-mb` caps per-file size.
- Media belongs to the original creators — personal archiving only.

MIT License.

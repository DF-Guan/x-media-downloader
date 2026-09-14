<p align="center">
  <img src="web/logo.svg" width="120" alt="x-media-downloader logo">
</p>

<h1 align="center">x-media-downloader</h1>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="python 3.9+">
  <img src="https://img.shields.io/badge/deps-zero-lightgrey" alt="zero dependencies">
</p>

<p align="center"><b>Batch-download public X / Twitter images & videos — no login, no API keys.</b><br>
单账号 / 多账号 / 榜单 TopN / 全量归档，一条命令批量抓取原图原视频。</p>

Looking for a **Twitter video downloader**, **Twitter image downloader without login**,
or a scriptable **X media downloader**? This tool fetches the newest media posts
(photos + videos, original quality) from any public X account and saves them with
fully customizable folder / filename templates.

## Screenshot (real run: @elonmusk, no login)

```bash
python grab.py download --handles elonmusk --posts 5 --media-types image
# [1/1] @elonmusk: posts=5 ok=4 skip=0 fail=0
```

<p align="center">
  <img src="docs/screenshot-elonmusk.jpg" width="640" alt="elonmusk images downloaded by x-media-downloader">
</p>

## Features

- 🔓 **No X login** — works through a public mirror API, zero cookies/tokens
- 👤👥 **1 account, N accounts, TopN ranking, or full lists** (`--handles` / `--handles-file` / `--archive`)
- 🔢 **Posts per account configurable** — `--posts 0` downloads everything available
- 🖼️🎬 **Media filter** — images only / videos only / all, plus `--max-mb` size cap
- ✏️ **Editable naming** — folder + file templates with a constrained `{variable}` whitelist (webpage-friendly dropdowns)
- ⏯️ **Resume-safe** — existing files are skipped; `manifest.jsonl` + `summary.json` outputs; `--dry-run` preview
- 🌐 **Web-ready** — local HTTP API + vanilla-JS demo page, easy to merge into your site
- 📦 **Zero dependencies** — Python 3.9+ stdlib only
- 🤖 **Agent skill** included (`skill/SKILL.md`)

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

# Top 15 from a gallery archive.json source
python grab.py download --archive https://host/data/archive.json --top 15 --posts 20

# dry-run: list only, download nothing
python grab.py download --handles Anaimiya --posts 5 --dry-run
```

All options with defaults: `config.example.json` (use `--config config.json`; CLI flags override it).

## Naming templates

| scope  | allowed `{variables}` |
|--------|-----------------------|
| folder | `{handle}` `{name}` |
| file   | `{handle}` `{name}` `{date}` `{date_dash}` `{time}` `{tweet_id}` `{seq}` `{ext}` `{type}` |

- `{date}` = YYYYMMDD, `{date_dash}` = YYYY-MM-DD, `{time}` = HHMMSS (default UTC+8 Beijing, `--tz-offset` to change)
- `{seq}` = media index within one post, zero-padded (`--seq-width`, default 2 → `01`)
- `{type}` = image / video. File template **must** contain `{ext}`.
- Illegal filename characters are sanitized automatically; collisions are skipped, never overwritten.

Check first: `python grab.py validate --file-template "..."` (or `POST /api/validate` from a webpage).

## Webpage integration

```bash
python grab.py serve --port 8765   # demo page: http://127.0.0.1:8765
```

| endpoint | purpose |
|---|---|
| `GET /api/templates` | variable whitelist + defaults → render as fixed dropdowns |
| `POST /api/validate` | verify templates before starting |
| `POST /api/jobs` | start job (`handles[]` or `archive`+`top`, `posts` 0=all, `media_types`, templates…) → `{id}` |
| `GET /api/jobs` / `GET /api/jobs/<id>` | poll progress (`done_users/total_users/current`), `summary` when finished |

`web/index.html` is a minimal dependency-free example to copy into your site.

## Project layout

```
grab.py                 CLI (download / validate / serve)
server.py               local HTTP API + static demo page
config.example.json     every option with defaults
x_media_downloader/     core library (importable, zero deps)
  fxtwitter.py          mirror-API client with pagination
  sources.py            handles list / txt / archive.json
  naming.py             template whitelist + sanitizer
  downloader.py         streaming download, retry, size cap
  jobs.py               N accounts × M posts orchestrator
web/                    demo UI + logo.svg
skill/SKILL.md          agent skill
```

## FAQ

**Why no login?** X timelines now require auth, but public posts are mirrored by
FxTwitter's API — this tool reads the mirror, so no cookies or API keys are needed.

**How many posts can I get?** `--posts 0` paginates until the mirror's timeline ends
(usually hundreds of media posts per account).

**Why are downloads slow / huge?** Creators post mostly video; one 1080p clip can be
tens of MB. Use `--media-types image` or `--max-mb` to slim a run.

**Rate limits?** Keep the default polite sleeps; if the mirror throttles you, wait and
re-run — finished files are skipped automatically.

## Disclaimer

Public posts only. Media belongs to the original creators — personal archiving only.
Not affiliated with X Corp; the logo here is an original design.

MIT License.

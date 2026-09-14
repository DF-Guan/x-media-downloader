"""Editable-but-constrained naming templates.

Only whitelisted ``{variables}`` are allowed, so a webpage UI can offer
them as fixed dropdown chips instead of free text:

- folder template vars: {handle} {name}
- file template vars:   {handle} {name} {date} {date_dash} {time}
                        {tweet_id} {seq} {ext} {type}

``{seq}`` is the 1-based media index inside one post, zero-padded to
``seq_width`` (default 2 -> 01, 02 ...).
"""

import re
import string

DIR_VARS = ("handle", "name")
FILE_VARS = (
    "handle",
    "name",
    "date",  # YYYYMMDD
    "date_dash",  # YYYY-MM-DD
    "time",  # HHMMSS
    "tweet_id",
    "seq",
    "ext",
    "type",  # image | video
)

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def template_fields(tpl):
    """List ``{var}`` names used in a template (plain names only)."""
    return [f for _, f, _, _ in string.Formatter().parse(tpl) if f]


def validate_template(tpl, kind="file"):
    """Raise ValueError if the template uses unknown variables."""
    allowed = FILE_VARS if kind == "file" else DIR_VARS
    unknown = [f for f in template_fields(tpl) if f not in allowed]
    if unknown:
        raise ValueError(
            f"unknown variable(s) {unknown} in {kind} template; "
            f"allowed: {list(allowed)}"
        )
    if kind == "file" and "ext" not in template_fields(tpl):
        raise ValueError("file template must contain {ext}")
    return True


def render(tpl, values, seq_width=2):
    vals = dict(values)
    if "seq" in vals:
        vals["seq"] = f"{int(vals['seq']):0{seq_width}d}"
    return tpl.format(**vals)


def sanitize(name, max_len=150):
    """Make a filename safe on Windows/macOS/Linux."""
    name = _ILLEGAL.sub("_", name).strip().rstrip(" .")
    return name[:max_len] if len(name) > max_len else name

"""Account sources: explicit list / txt file / archive.json (path or URL)."""

import json
import urllib.request

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _load_json_doc(source):
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    with open(source, encoding="utf-8") as f:
        return json.load(f)


def _entry_to_account(entry):
    if isinstance(entry, str):
        return {"handle": entry.strip().lstrip("@"), "name": ""}
    if isinstance(entry, dict):
        handle = entry.get("screen_name") or entry.get("handle") or ""
        return {"handle": handle.strip().lstrip("@"), "name": entry.get("name", "")}
    return None


def load_handles(handles=None, handles_file=None, archive=None,
                 top=0, offset=0, include_suspended=False):
    """Collect ``[{"handle", "name"}]`` preserving order, de-duplicated."""
    out = []
    if handles:
        for h in handles:
            if h and h.strip():
                out.append({"handle": h.strip().lstrip("@"), "name": ""})
    if handles_file:
        if handles_file.endswith(".json"):
            doc = _load_json_doc(handles_file)
            items = doc if isinstance(doc, list) else doc.get("data", doc.get("items", []))
            for entry in items:
                acc = _entry_to_account(entry)
                if acc and acc["handle"]:
                    out.append(acc)
        else:  # plain txt, one handle per line, '#' comments
            with open(handles_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        out.append({"handle": line.lstrip("@"), "name": ""})
    if archive:
        doc = _load_json_doc(archive)
        items = doc if isinstance(doc, list) else doc.get("data", [])
        if not include_suspended:
            items = [e for e in items if not (e.get("is_suspended") if isinstance(e, dict) else False)]
        items = sorted(items, key=lambda e: e.get("total_clicks", 0)
                       if isinstance(e, dict) else 0, reverse=True)
        items = items[offset:]
        if top > 0:
            items = items[:top]
        for entry in items:
            acc = _entry_to_account(entry)
            if acc and acc["handle"]:
                out.append(acc)
    seen, unique = set(), []
    for acc in out:
        key = acc["handle"].lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(acc)
    return unique

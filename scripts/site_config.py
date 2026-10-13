import json
from pathlib import Path
from urllib.parse import urlsplit


def validate_url(value):
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ValueError("A website URL is required and must be at most 2048 characters.")

    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Website URLs must use http:// or https:// and include a hostname.")
    if parsed.username or parsed.password:
        raise ValueError("Website URLs must not contain embedded credentials.")
    if any(character.isspace() for character in value):
        raise ValueError("Website URLs must not contain whitespace.")
    return value


def validate_monitors(monitors):
    if not isinstance(monitors, list):
        raise ValueError("monitors.json must contain a list.")

    ids = set()
    names = set()
    urls = set()
    for monitor in monitors:
        if not isinstance(monitor, dict):
            raise ValueError("Each monitor must be an object.")
        monitor_id = monitor.get("id")
        name = monitor.get("name")
        url = validate_url(monitor.get("url"))
        if not isinstance(monitor_id, str) or not monitor_id:
            raise ValueError("Each monitor must have an id.")
        if not isinstance(name, str) or not name.strip() or len(name) > 80:
            raise ValueError("Each monitor must have a name between 1 and 80 characters.")
        if monitor_id in ids:
            raise ValueError(f"Duplicate monitor id: {monitor_id}")
        if name.casefold() in names:
            raise ValueError(f"Duplicate monitor name: {name}")
        if url in urls:
            raise ValueError(f"Duplicate monitor URL: {url}")
        ids.add(monitor_id)
        names.add(name.casefold())
        urls.add(url)
    return monitors


def read_json(path, default=None):
    file_path = Path(path)
    if not file_path.exists() and default is not None:
        return default
    with file_path.open(encoding="utf-8") as source:
        return json.load(source)


def write_json(path, value):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = file_path.with_suffix(file_path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as destination:
        json.dump(value, destination, indent=2, ensure_ascii=False)
        destination.write("\n")
    temporary_path.replace(file_path)

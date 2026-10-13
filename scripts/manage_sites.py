import os
import uuid
from pathlib import Path

from scripts.site_config import read_json, validate_monitors, validate_url, write_json


def apply_operation(monitors, operation, existing_url="", name="", url=""):
    validate_monitors(monitors)
    if operation == "check":
        return monitors

    if operation == "add":
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Enter a display name for the new website.")
        validate_url(url)
        if any(site["url"] == url for site in monitors):
            raise ValueError(f"That URL is already monitored: {url}")
        if any(site["name"].casefold() == cleaned_name.casefold() for site in monitors):
            raise ValueError(f"That display name is already used: {cleaned_name}")
        monitors.append({
            "id": uuid.uuid4().hex,
            "name": cleaned_name,
            "url": url,
        })
        return validate_monitors(monitors)

    if operation not in {"edit", "remove"}:
        raise ValueError("Choose check, add, edit, or remove.")
    if not existing_url:
        raise ValueError("Choose the existing website by entering its exact URL.")

    index = next((i for i, site in enumerate(monitors) if site["url"] == existing_url), None)
    if index is None:
        raise ValueError(f"No monitored website matches: {existing_url}")

    if operation == "remove":
        del monitors[index]
        return monitors

    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Enter a display name for the edited website.")
    validate_url(url)
    if any(i != index and site["url"] == url for i, site in enumerate(monitors)):
        raise ValueError(f"That URL is already monitored: {url}")
    if any(i != index and site["name"].casefold() == cleaned_name.casefold()
           for i, site in enumerate(monitors)):
        raise ValueError(f"That display name is already used: {cleaned_name}")

    monitors[index]["name"] = cleaned_name
    monitors[index]["url"] = url
    return validate_monitors(monitors)


def main():
    config_path = Path("monitors.json")
    monitors = read_json(config_path)
    updated = apply_operation(
        monitors,
        operation=os.environ.get("SITE_OPERATION", "check"),
        existing_url=os.environ.get("SITE_EXISTING_URL", ""),
        name=os.environ.get("SITE_NAME", ""),
        url=os.environ.get("SITE_URL", ""),
    )
    if updated != monitors or os.environ.get("SITE_OPERATION", "check") != "check":
        write_json(config_path, updated)
    print(f"Monitor configuration contains {len(updated)} website(s).")


if __name__ == "__main__":
    main()
